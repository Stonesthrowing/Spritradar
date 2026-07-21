"""Stündliche Momentaufnahme der Preise -> data/intraday.json.

Läuft per GitHub Actions stündlich. Speichert je Standort den aktuell
günstigsten E10-Preis mit Uhrzeit, damit echte Tagesverläufe entstehen.
"""

from __future__ import annotations

import datetime as dt
import sys
from zoneinfo import ZoneInfo

from . import intraday as itd
from .config import load_config, load_secrets
from .tankerkoenig import fetch_stations


def run() -> int:
    cfg = load_config()
    secrets = load_secrets()
    tz = ZoneInfo(cfg.timezone)
    now = dt.datetime.now(tz)
    date = now.date().isoformat()
    time_str = now.strftime("%H:%M")

    data = itd.load_intraday()
    wrote = 0
    for loc in cfg.locations:
        try:
            stations = fetch_stations(
                secrets.tankerkoenig_api_key, loc.lat, loc.lng, loc.radius_km, cfg.fuel_type
            )
        except Exception as exc:
            print(f"[collect] Fehler bei {loc.name}: {exc}", file=sys.stderr)
            continue
        if not stations:
            continue
        itd.append_snapshot(data, loc.plz, date, time_str, stations[0].price)
        wrote += 1

    # Alte Tage aufräumen.
    keep = {(now.date() - dt.timedelta(days=d)).isoformat() for d in range(itd.KEEP_DAYS)}
    itd.prune(data, keep)

    itd.save_intraday(data)
    print(f"[collect] {time_str}: {wrote} Standort(e) gespeichert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
