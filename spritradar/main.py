"""Orchestrierung: Preise holen -> bewerten -> Historie speichern -> senden.

Läuft täglich via GitHub Actions. Die eigentliche Sendezeit (7:30) steuert
der cron-Trigger; dieses Skript prüft zusätzlich die lokale Uhrzeit
(Sommer-/Winterzeit) und sendet pro Tag nur einmal.
"""

from __future__ import annotations

import datetime as dt
import os
import sys
from zoneinfo import ZoneInfo

from . import history as hist
from . import telegram
from .config import load_config, load_secrets
from .message import build_message
from .scoring import score_today
from .tankerkoenig import fetch_stations


def _within_send_window(now_local: dt.datetime, window: tuple[int, int]) -> bool:
    return window[0] <= now_local.hour < window[1]


def run() -> int:
    cfg = load_config()
    secrets = load_secrets()
    tz = ZoneInfo(cfg.timezone)
    now_local = dt.datetime.now(tz)
    today = now_local.date().isoformat()

    forced = os.environ.get("FORCE", "").strip() not in ("", "0", "false", "False")

    data = hist.load_history()

    # Sende-Gate: außerhalb des Zeitfensters oder heute schon gesendet -> nur
    # bei FORCE (manueller Start) trotzdem weiter.
    if not forced:
        if not _within_send_window(now_local, cfg.send_window_local_hours):
            print(f"[Spritradar] {now_local:%H:%M} {cfg.timezone} außerhalb Sendefenster – überspringe.")
            return 0
        if data.get("last_sent_date") == today:
            print(f"[Spritradar] Heute ({today}) bereits gesendet – überspringe.")
            return 0

    results = []
    for loc in cfg.locations:
        try:
            stations = fetch_stations(
                secrets.tankerkoenig_api_key, loc.lat, loc.lng, loc.radius_km, cfg.fuel_type
            )
        except Exception as exc:  # Netzwerk/API-Fehler pro Standort tolerieren
            print(f"[Spritradar] Fehler bei {loc.name}: {exc}", file=sys.stderr)
            continue
        if not stations:
            print(f"[Spritradar] Keine geöffnete Tankstelle mit E10 bei {loc.name}.", file=sys.stderr)
            continue

        cheapest = stations[0]
        recent = hist.recent_prices(data, loc.plz, cfg.history_window_days, exclude_date=today)
        score = score_today(cheapest.price, recent, cfg.min_history_for_score)
        results.append((loc.name, loc.emoji, score, cheapest.label))

        hist.append_reading(data, loc.plz, today, cheapest.price, cheapest.label)

    if not results:
        print("[Spritradar] Keine Ergebnisse – nichts zu senden.", file=sys.stderr)
        return 1

    text = build_message(now_local, results)
    print("----- Nachricht -----")
    print(text)
    print("---------------------")

    chat_id = telegram.resolve_chat_id(secrets.telegram_bot_token, secrets.telegram_chat_id)
    if not chat_id:
        print(
            "[Spritradar] Keine Chat-ID verfügbar. Schreibe dem Bot einmalig eine "
            "Nachricht (z. B. /start) und setze dann das Secret TELEGRAM_CHAT_ID.",
            file=sys.stderr,
        )
        return 2

    telegram.send_message(secrets.telegram_bot_token, chat_id, text)
    print(f"[Spritradar] Gesendet an Chat {chat_id}.")

    # Historie & Sende-Marker persistieren (Workflow committet die Datei).
    data["last_sent_date"] = today
    hist.save_history(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
