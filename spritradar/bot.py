"""Telegram-Poller: antwortet auf „Graphs" mit den drei Tagesverlauf-Charts.

Läuft per GitHub Actions alle paar Minuten (GitHub kann nicht dauerhaft lauschen),
holt neue Nachrichten via getUpdates und schickt bei „Graphs" das Chart-PNG zurück.
Der Update-Offset wird in data/bot_state.json gemerkt, damit nichts doppelt läuft.
"""

from __future__ import annotations

import datetime as dt
import json
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

from . import charts
from . import history as hist
from . import intraday as itd
from . import telegram
from .config import REPO_ROOT, load_config, load_secrets

STATE_PATH = REPO_ROOT / "data" / "bot_state.json"
TRIGGER = "graph"  # matcht "Graphs", "/graphs", "graph" …
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


def run() -> int:
    cfg = load_config()
    secrets = load_secrets()
    tz = ZoneInfo(cfg.timezone)

    offset = _load_offset()
    updates = telegram.get_updates(secrets.telegram_bot_token, offset=offset)
    if not updates:
        print("[bot] keine neuen Updates.")
        return 0

    max_id = offset - 1 if offset else 0
    handled = 0
    for upd in updates:
        max_id = max(max_id, int(upd.get("update_id", 0)))
        msg = upd.get("message") or upd.get("edited_message") or {}
        text = (msg.get("text") or "").strip().lower()
        chat_id = (msg.get("chat") or {}).get("id")
        if not chat_id or TRIGGER not in text:
            continue
        try:
            png, caption = _make_charts(cfg, dt.datetime.now(tz))
            telegram.send_photo(secrets.telegram_bot_token, chat_id, png, caption)
            handled += 1
            print(f"[bot] Charts an Chat {chat_id} gesendet.")
        except Exception as exc:
            print(f"[bot] Fehler beim Senden an {chat_id}: {exc}")

    _save_offset(max_id + 1)
    print(f"[bot] {len(updates)} Update(s) verarbeitet, {handled} Chart-Antwort(en).")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
