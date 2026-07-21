"""Intraday-Preisverläufe: sammeln, speichern und modellieren.

Die freie Tankerkönig-API liefert nur den aktuellen Preis. Ein stündlicher Job
schreibt daher Momentaufnahmen in data/intraday.json. Für Stunden ohne echte
Messung (Rest von heute, ganzer morgiger Tag) wird ein typisches deutsches
Tagesprofil ans bekannte Preisniveau angelegt.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path

from .config import REPO_ROOT

INTRADAY_PATH = REPO_ROOT / "data" / "intraday.json"

# Typisches E10-Tagesprofil: relativer Aufschlag in ct (hoch = teuer).
# Morgens teuer (Peak ~6 Uhr), abends günstig (~18–21 Uhr). Näherung nach
# bekanntem ADAC-Muster; wird durch echte Messungen zunehmend ersetzt.
SHAPE = {
    0: 6.0, 1: 6.0, 2: 6.0, 3: 6.0, 4: 6.0, 5: 6.5, 6: 6.0, 7: 5.0,
    8: 3.5, 9: 2.0, 10: 1.0, 11: 0.0, 12: -1.0, 13: -0.5, 14: 0.0, 15: 0.5,
    16: 0.0, 17: -1.5, 18: -3.5, 19: -4.0, 20: -4.5, 21: -5.0, 22: -3.0, 23: 0.0,
    24: 6.0,
}
REF_HOUR = 6  # Stunde, auf die sich die Morgen-Referenz bezieht
KEEP_DAYS = 4  # so viele Tage Intraday-Historie behalten


# ---------------------------------------------------------------- Speicher ---
def load_intraday(path: Path | str = INTRADAY_PATH) -> dict:
    p = Path(path)
    if not p.exists():
        return {"locations": {}}
    data = json.loads(p.read_text(encoding="utf-8"))
    data.setdefault("locations", {})
    return data


def save_intraday(data: dict, path: Path | str = INTRADAY_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_snapshot(data: dict, plz: str, date: str, time_str: str, price: float) -> None:
    day = data.setdefault("locations", {}).setdefault(plz, {}).setdefault(date, [])
    day.append({"t": time_str, "price": round(float(price), 3)})


def prune(data: dict, keep_dates: set[str]) -> None:
    for plz, days in data.get("locations", {}).items():
        for d in list(days):
            if d not in keep_dates:
                del days[d]


def day_points(data: dict, plz: str, date: str) -> list[tuple[float, float]]:
    """Gemessene (Stunde, Preis) eines Tages, nach Stunde sortiert."""
    out = []
    for e in data.get("locations", {}).get(plz, {}).get(date, []):
        try:
            hh, mm = e["t"].split(":")
            out.append((int(hh) + int(mm) / 60.0, float(e["price"])))
        except (ValueError, KeyError):
            continue
    out.sort(key=lambda x: x[0])
    return out


# ------------------------------------------------------------------ Modell ---
def _offset(hour: float, shape: dict = SHAPE) -> float:
    h0 = int(hour) % 24
    frac = hour - int(hour)
    return shape[h0] + (shape[h0 + 1] - shape[h0]) * frac


def learn_shape(store: dict, exclude_date: str | None = None,
                min_days: int = 5, min_hours: int = 8) -> tuple[dict, bool]:
    """Tagesprofil aus gesammelten Daten lernen (relativer ct-Aufschlag je Stunde).

    Nur Tage mit ausreichend Stundenabdeckung zählen; der heutige (unvollständige)
    Tag wird ausgeschlossen. Reicht die Datenbasis nicht, kommt das statische
    Standardprofil zurück. Rückgabe: (shape, gelernt?).
    """
    sums: dict[int, float] = {}
    counts: dict[int, int] = {}
    good_days = 0

    for days in store.get("locations", {}).values():
        for date, entries in days.items():
            if date == exclude_date:
                continue
            by_hour: dict[int, float] = {}
            for e in entries:
                try:
                    hh = int(e["t"].split(":")[0])
                    by_hour[hh] = float(e["price"])  # letzter Wert der Stunde gewinnt
                except (ValueError, KeyError):
                    continue
            if len(by_hour) < min_hours:
                continue
            mean = sum(by_hour.values()) / len(by_hour)
            for hh, price in by_hour.items():
                sums[hh] = sums.get(hh, 0.0) + (price - mean) * 100.0
                counts[hh] = counts.get(hh, 0) + 1
            good_days += 1

    if good_days < min_days:
        return SHAPE, False

    shape = {}
    for h in range(25):
        hh = h % 24
        if counts.get(hh):
            shape[h] = sums[hh] / counts[hh]
        else:
            shape[h] = SHAPE[h]  # fehlende Stunde -> Standardprofil
    return shape, True


def model_curve(anchor_price: float, anchor_hour: float, h_start: float, h_end: float,
                step: float = 0.5, shape: dict = SHAPE) -> list[tuple[float, float]]:
    """Modellierte Kurve zwischen h_start und h_end, verankert am Referenzpunkt."""
    pts = []
    h = h_start
    base = _offset(anchor_hour, shape)
    while h <= h_end + 1e-9:
        pts.append((h, anchor_price + (_offset(h, shape) - base) / 100.0))
        h += step
    return pts


@dataclass
class DaySeries:
    real: list[tuple[float, float]]   # gemessen
    model: list[tuple[float, float]]  # extrapoliert/modelliert


def build_day(mode: str, real: list[tuple[float, float]], anchor_price: float | None,
              now_hour: float, shape: dict = SHAPE) -> DaySeries:
    """Real + Modell für einen Tag zusammensetzen.

    mode: "past" (gestern), "today", "future" (morgen).
    """
    if mode == "past":
        if real:
            return DaySeries(real=real, model=[])
        if anchor_price is not None:
            return DaySeries(real=[], model=model_curve(anchor_price, REF_HOUR, 0, 24, shape=shape))
        return DaySeries(real=[], model=[])

    if mode == "today":
        if real:
            last_h, last_p = real[-1]
            model = model_curve(last_p, last_h, last_h, 24, shape=shape)
            return DaySeries(real=real, model=model)
        if anchor_price is not None:
            # noch keine Messung heute -> ganzer Tag modelliert
            model = model_curve(anchor_price, REF_HOUR, 0, 24, shape=shape)
            return DaySeries(real=[], model=model)
        return DaySeries(real=[], model=[])

    # future
    if anchor_price is not None:
        return DaySeries(real=[], model=model_curve(anchor_price, REF_HOUR, 0, 24, shape=shape))
    return DaySeries(real=[], model=[])
