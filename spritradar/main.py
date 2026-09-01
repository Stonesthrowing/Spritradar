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

from . import analysis
from . import history as hist
from . import intraday as itd
from . import market as market_mod
from . import news as news_mod
from . import plan as plan_mod
from . import telegram
from .config import load_config, load_secrets
from .message import build_tankplan
from .tankerkoenig import fetch_stations, find_preferred


def _within_send_window(now_local: dt.datetime, after: dt.time, until: dt.time) -> bool:
    return after <= now_local.time() <= until


def build_report(cfg, secrets, now_local: dt.datetime, data: dict) -> str | None:
    """Preise holen, bewerten und die fertige Tankplan-Nachricht bauen.

    Schreibt die Tages-Historie in `data` fort (Speichern übernimmt der Aufrufer).
    Gibt None zurück, wenn kein einziger Standort Daten geliefert hat.
    Wird sowohl vom Tageslauf als auch vom „go"-Befehl des Bots benutzt.
    """
    today = now_local.date().isoformat()
    intraday_store = itd.load_intraday()
    plans = []
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

        # Bevorzugte Station bestimmen (der Preis, den du zahlst); sonst günstigste.
        favorite = None
        favorite_label = ""
        preferred_prices = {}
        for spec in loc.preferred:
            match = find_preferred(stations, spec)
            if match is not None:
                preferred_prices[spec.label] = round(match.price, 3)
                if favorite is None:
                    favorite = match
                    favorite_label = spec.label
            else:
                print(f"[Spritradar] Favorit nicht gefunden: {spec.label}", file=sys.stderr)
        current_price = favorite.price if favorite else cheapest.price
        if favorite is None:
            favorite_label = f"{cheapest.label} (günstigste)"

        market = market_mod.market_context(stations, current_price)
        plans.append(
            plan_mod.build_plan(
                loc.name, loc.emoji, now_local, current_price, market, intraday_store, loc.plz,
                favorite_label=favorite_label,
                cheapest_label=cheapest.label,
                cheapest_price=cheapest.price,
            )
        )

        # Tages-Historie weiterpflegen (Tagesminimum + Favorit) für Charts/Verlauf.
        hist.append_reading(
            data, loc.plz, today, cheapest.price, cheapest.label, preferred=preferred_prices
        )

    if not plans:
        print("[Spritradar] Keine Ergebnisse – nichts zu senden.", file=sys.stderr)
        return None

    # Nachrichtenlage (optional, darf den Versand nie blockieren).
    insight = None
    if cfg.news.enabled:
        try:
            headlines = news_mod.fetch_headlines(cfg.news.query, cfg.news.max_headlines)
            insight = analysis.analyze(headlines, cfg.news.model, secrets.anthropic_api_key)
            if insight:
                print(f"[Spritradar] News-Analyse ({insight.source}): {insight.tendency}")
        except Exception as exc:
            print(f"[Spritradar] News übersprungen: {exc}", file=sys.stderr)

    return build_tankplan(now_local, plans, news=insight)


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
        if not _within_send_window(now_local, cfg.send_after, cfg.send_until):
            print(f"[Spritradar] {now_local:%H:%M} {cfg.timezone} außerhalb Sendefenster – überspringe.")
            return 0
        if data.get("last_sent_date") == today:
            print(f"[Spritradar] Heute ({today}) bereits gesendet – überspringe.")
            return 0

    text = build_report(cfg, secrets, now_local, data)
    if text is None:
        return 1
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
