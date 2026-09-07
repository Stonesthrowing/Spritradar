"""Telegram-Poller: reagiert auf die Befehle im Chat.

    go      -> aktueller Tankplan (dieselbe Nachricht wie der Tageslauf)
    graphs  -> drei Tagesverlauf-Charts (gestern / heute / morgen)

Es gibt keinen Tageszeitplan mehr: Die Nachricht kommt nur noch auf „go".
Der Update-Offset liegt in data/bot_state.json, damit ein Befehl nicht doppelt
beantwortet wird.

Zwei Betriebsarten (siehe run()):
  POLL_SECONDS leer/0  -> einmal nachsehen (Mini-PC-Task alle 2 Minuten)
  POLL_SECONDS > 0     -> so lange lauschen (GitHub Actions, Long-Polling);
                          nebenbei stuendlich eine Preismessung schreiben
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import tempfile
import time
from pathlib import Path
from zoneinfo import ZoneInfo

from . import charts
from . import collect
from . import history as hist
from . import intraday as itd
from . import main as main_mod
from . import telegram
from .config import REPO_ROOT, load_config, load_secrets

STATE_PATH = REPO_ROOT / "data" / "bot_state.json"
CHART_TRIGGER = "graph"  # matcht "Graphs", "/graphs", "graph" …
PLAN_TRIGGER = "go"      # matcht "go", "/go", "Go" – als ganzes Wort
# Ganzes Wort, damit "google", "Bogen" o. Ä. den Tankplan nicht auslösen.
_WORD_GO = re.compile(rf"(?<!\w){PLAN_TRIGGER}(?!\w)")
# Wie lange eine einzelne Long-Poll-Anfrage offen bleibt (Telegram erlaubt <=50).
LONG_POLL_SECONDS = 50
CAPTION_BASE = (
    "⛽ Tagesverlauf Super E10 – gestern / heute / morgen.\n"
    "Durchgezogen = gemessen, gestrichelt = Prognose."
)


def _load_offset() -> int | None:
    if STATE_PATH.exists():
        try:
            return int(json.loads(STATE_PATH.read_text(encoding="utf-8")).get("offset"))
        except (ValueError, TypeError, json.JSONDecodeError):
            return None
    return None


def _save_offset(offset: int) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({"offset": offset}) + "\n", encoding="utf-8")


def _make_charts(cfg, now_local) -> tuple[str, str]:
    store = itd.load_intraday()
    history = hist.load_history()
    days, now_hour, learned = charts.build_days(cfg, store, history, now_local)
    out = Path(tempfile.gettempdir()) / "spritradar_charts.png"
    profil = "gelerntes Tagesprofil" if learned else "typisches Tagesprofil (noch wenig Daten)"
    caption = f"{CAPTION_BASE}\nPrognose-Basis: {profil}."
    return charts.render(days, now_hour, out), caption


def _handle_batch(cfg, secrets, tz, updates: list[dict], offset: int | None) -> int:
    """Einen Schwung Updates beantworten. Gibt die Zahl der Antworten zurück."""
    max_id = offset - 1 if offset else 0
    handled = 0
    history = None
    for upd in updates:
        max_id = max(max_id, int(upd.get("update_id", 0)))
        msg = upd.get("message") or upd.get("edited_message") or {}
        text = (msg.get("text") or "").strip().lower()
        chat_id = (msg.get("chat") or {}).get("id")
        if not chat_id:
            continue

        if CHART_TRIGGER in text:
            try:
                png, caption = _make_charts(cfg, dt.datetime.now(tz))
                telegram.send_photo(secrets.telegram_bot_token, chat_id, png, caption)
                handled += 1
                print(f"[bot] Charts an Chat {chat_id} gesendet.")
            except Exception as exc:
                print(f"[bot] Fehler beim Chart-Versand an {chat_id}: {exc}")
        elif _WORD_GO.search(text):
            try:
                # Historie einmal laden und über alle „go" hinweg fortschreiben.
                if history is None:
                    history = hist.load_history()
                now_local = dt.datetime.now(tz)
                report = main_mod.build_report(cfg, secrets, now_local, history)
                if report is None:
                    telegram.send_message(
                        secrets.telegram_bot_token,
                        chat_id,
                        "Gerade keine Preisdaten verfügbar – bitte gleich nochmal „go\" senden.",
                    )
                else:
                    telegram.send_message(secrets.telegram_bot_token, chat_id, report)
                    history["last_sent_date"] = now_local.date().isoformat()
                    handled += 1
                    print(f"[bot] Tankplan an Chat {chat_id} gesendet.")
            except Exception as exc:
                print(f"[bot] Fehler beim Tankplan-Versand an {chat_id}: {exc}")

    if history is not None:
        hist.save_history(history)
    _save_offset(max_id + 1)
    print(f"[bot] {len(updates)} Update(s) verarbeitet, {handled} Antwort(en).")
    return handled


def run() -> int:
    """Einmal nachsehen – oder mit POLL_SECONDS>0 eine Weile lauschen.

    Einmal-Modus (POLL_SECONDS leer/0) ist der Mini-PC-Weg: Ein Task ruft das
    Skript alle 2 Minuten auf.

    Lausch-Modus ist der GitHub-Weg. Hintergrund: GitHub liefert geplante Läufe
    massiv gedrosselt aus – von 144 geplanten Läufen am Tag (`*/10`) kamen
    real nur ~3 an. Ein kurzer Poll pro Lauf hiesse also bis zu 2 h Wartezeit
    auf „go". Deshalb bleibt der Lauf, der durchkommt, per Long-Polling offen
    und antwortet in Sekunden, statt einmal kurz nachzusehen.
    """
    cfg = load_config()
    secrets = load_secrets()
    tz = ZoneInfo(cfg.timezone)

    try:
        poll_seconds = int(os.environ.get("POLL_SECONDS", "0").strip() or 0)
    except ValueError:
        poll_seconds = 0

    if poll_seconds <= 0:
        offset = _load_offset()
        updates = telegram.get_updates(secrets.telegram_bot_token, offset=offset)
        if not updates:
            print("[bot] keine neuen Updates.")
            return 0
        _handle_batch(cfg, secrets, tz, updates, offset)
        return 0

    deadline = time.monotonic() + poll_seconds
    print(f"[bot] Lausche {poll_seconds // 60} Minuten auf „go\" / „graphs\" …")
    total = 0
    errors = 0
    collected_hour = None
    while time.monotonic() < deadline:
        # Der Lauscher laeuft ohnehin durch -> die stuendliche Preismessung
        # gleich hier miterledigen, statt dafuer einen zweiten Zeitplan zu
        # brauchen. Darf den Lauscher nie umbringen.
        hour = dt.datetime.now(tz).hour
        if hour != collected_hour:
            collected_hour = hour
            try:
                collect.run()
            except Exception as exc:
                print(f"[bot] Preismessung übersprungen: {exc}")

        # Long-Poll nie über die Deadline hinaus, damit der Job planbar endet.
        wait = int(min(LONG_POLL_SECONDS, deadline - time.monotonic()))
        if wait <= 0:
            break
        offset = _load_offset()
        try:
            updates = telegram.get_updates(
                secrets.telegram_bot_token, offset=offset, long_poll=wait
            )
            errors = 0
        except Exception as exc:
            # Netzwerkaussetzer dürfen den Lauscher nicht beenden.
            errors += 1
            print(f"[bot] getUpdates fehlgeschlagen ({errors}): {exc}")
            if errors >= 5:
                print("[bot] zu viele Fehler hintereinander – beende.")
                return 1
            # Nie über die Deadline hinaus schlafen.
            time.sleep(max(0, min(60, 5 * errors, deadline - time.monotonic())))
            continue
        if updates:
            total += _handle_batch(cfg, secrets, tz, updates, offset)

    print(f"[bot] Lauschzeit vorbei, {total} Antwort(en) gesendet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
