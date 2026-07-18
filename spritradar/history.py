"""Selbst gesammelte Preishistorie.

Die freie Tankerkönig-API liefert nur aktuelle Preise, keine Historie.
Deshalb speichern wir jeden Morgen den günstigsten E10-Preis je Standort
in data/history.json und lassen die Datei über die Zeit wachsen (der
GitHub-Actions-Workflow committet sie zurück ins Repo).
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import DEFAULT_HISTORY_PATH


def load_history(path: Path | str = DEFAULT_HISTORY_PATH) -> dict:
    p = Path(path)
    if not p.exists():
        return {"last_sent_date": None, "locations": {}}
    data = json.loads(p.read_text(encoding="utf-8"))
    data.setdefault("last_sent_date", None)
    data.setdefault("locations", {})
    return data


def save_history(data: dict, path: Path | str = DEFAULT_HISTORY_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def recent_prices(data: dict, plz: str, window_days: int, exclude_date: str) -> list[float]:
    """Preise der letzten `window_days` Einträge, ohne den heutigen Tag."""
    entries = data.get("locations", {}).get(plz, [])
    prices = [
        float(e["min_price"])
        for e in entries
        if e.get("date") != exclude_date and e.get("min_price") is not None
    ]
    return prices[-window_days:]


def append_reading(
    data: dict,
    plz: str,
    date: str,
    min_price: float,
    station: str,
    preferred: dict | None = None,
) -> None:
    """Heutigen Messwert ablegen (idempotent: überschreibt gleichen Tag)."""
    entries = data.setdefault("locations", {}).setdefault(plz, [])
    entries[:] = [e for e in entries if e.get("date") != date]
    entry = {"date": date, "min_price": round(float(min_price), 3), "station": station}
    if preferred:
        entry["preferred"] = preferred
    entries.append(entry)
    entries.sort(key=lambda e: e["date"])
