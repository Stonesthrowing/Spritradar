"""Regime-bewusstes Tages-Prognose- und Bewertungsmodell (12-Uhr-Regel).

Rechtslage (KPAnG, seit 01.04.2026): Preise dürfen nur 1x täglich um 12:00 steigen,
Senkungen jederzeit. Daraus folgt hart:
- Vor 12:00 kann der Preis NICHT steigen -> Warten bis kurz vor 12 ist risikolos.
- Um 12:00 ein einmaliger Sprung (ADAC-Mittel ~14,6 ct bei E10).
- Nach 12:00 nur noch Senkungen -> abends oft am günstigsten.

Das Modell ist additiv und nachvollziehbar: es schätzt aus der eigenen Historie den
12-Uhr-Sprung sowie das erreichbare Tagestief und leitet daraus Empfehlung + Score ab.
Alle Preise in €, Deltas in ct.
"""

from __future__ import annotations

import datetime as dt
import statistics
from dataclasses import dataclass, field

from . import intraday as itd
from .market import MarketContext

EVENING_START, EVENING_END = 17.0, 21.5  # Abendfenster (Std.)
PRENOON_WINDOW = (11.0, 11.83)           # ~11:00–11:50 (kurz vor dem Sprung)


@dataclass
class Window:
    name: str          # "jetzt" | "vor12" | "abend"
    label_time: str
    price_low: float
    price_high: float
    reachable: bool
    score: int = 0

    @property
    def repr_price(self) -> float:
        return (self.price_low + self.price_high) / 2


@dataclass
class DayPlan:
    name: str
    emoji: str
    current_price: float             # Preis am Favoriten (dort tankst du normalerweise)
    market: MarketContext
    noon_jump_ct: float
    noon_jump_n: int
    windows: list[Window] = field(default_factory=list)
    best: Window | None = None
    recommendation: str = "NEUTRAL"   # WARTEN | TANKEN | NEUTRAL
    action_line: str = ""
    reasons: list[str] = field(default_factory=list)
    data_days: int = 0
    favorite_label: str = ""          # Name der bevorzugten Tankstelle
    cheapest_label: str = ""          # günstigste Station im Umkreis
    cheapest_price: float | None = None

    @property
    def detour_ct(self) -> float | None:
        """Ersparnis in ct, wenn statt des Favoriten die günstigste angefahren wird."""
        if self.cheapest_price is None:
            return None
        return round((self.current_price - self.cheapest_price) * 100, 1)

    @property
    def favorite_is_cheapest(self) -> bool:
        d = self.detour_ct
        return d is not None and d <= 0.05

    @property
    def confidence(self) -> str:
        if self.data_days >= 21:
            return "gut"
        if self.data_days >= 7:
            return "mittel"
        return "gering"


# ----------------------------------------------------------- Historie-Schätzer ---
def _past_days(store: dict, plz: str, today: str) -> list[str]:
    return sorted(d for d in store.get("locations", {}).get(plz, {}) if d != today)


def _prenoon_ref(points: list[tuple[float, float]]) -> float | None:
    """Referenzpreis eines Tages vor 12 Uhr (nächster Punkt zu REF_HOUR)."""
    pre = [(h, p) for h, p in points if h < 12.0]
    if not pre:
        return None
    return min(pre, key=lambda hp: abs(hp[0] - itd.REF_HOUR))[1]


def estimate_noon_jump(store: dict, plz: str, today: str) -> tuple[float, int]:
    jumps = []
    for d in _past_days(store, plz, today):
        pts = itd.day_points(store, plz, d)
        pre = [(h, p) for h, p in pts if h < 12.0]
        post = [(h, p) for h, p in pts if 12.0 <= h < 15.0]
        if pre and post:
            jump = (min(post, key=lambda hp: hp[0])[1] - max(pre, key=lambda hp: hp[0])[1]) * 100
            if jump > 0:  # nur echte Sprünge zählen
                jumps.append(jump)
    if not jumps:
        return itd.NOON_JUMP_DEFAULT_CT, 0
    return round(statistics.median(jumps), 1), len(jumps)


def _median_offset(store: dict, plz: str, today: str,
                   lo: float, hi: float) -> tuple[float, int]:
    """Median über Tage von (Tief im Fenster [lo,hi) − Vor-12-Referenz), in ct."""
    offs = []
    for d in _past_days(store, plz, today):
        pts = itd.day_points(store, plz, d)
        ref = _prenoon_ref(pts)
        win = [p for h, p in pts if lo <= h < hi]
        if ref is not None and win:
            offs.append((min(win) - ref) * 100)
    if not offs:
        return 0.0, 0
    return round(statistics.median(offs), 1), len(offs)


# --------------------------------------------------------------------- Scoring ---
def _score(repr_price: float, best_repr: float, market: MarketContext, data_days: int) -> int:
    ct_above = (repr_price - best_repr) * 100
    price_pts = max(0.0, min(70.0, 70.0 - 14.0 * ct_above))
    delta = market.delta_ct if market.delta_ct is not None else 0.0
    local_pts = max(0.0, min(20.0, 10.0 - 2.5 * delta))
    conf_pts = min(10, data_days)
    return int(round(max(0.0, min(100.0, price_pts + local_pts + conf_pts))))


def score_emoji(score: int) -> str:
    if score >= 70:
        return "🟢"
    if score >= 50:
        return "🟡"
    if score >= 30:
        return "🟠"
    return "🔴"


# ------------------------------------------------------------------- Hauptbau ---
def build_plan(name: str, emoji: str, now_local: dt.datetime, current_price: float,
               market: MarketContext, store: dict, plz: str,
               favorite_label: str = "", cheapest_label: str = "",
               cheapest_price: float | None = None) -> DayPlan:
    today = now_local.date().isoformat()
    now_h = now_local.hour + now_local.minute / 60.0
    data_days = len(_past_days(store, plz, today))

    noon_jump, jump_n = estimate_noon_jump(store, plz, today)
    evening_off, _ = _median_offset(store, plz, today, EVENING_START, EVENING_END)
    prenoon_dip, _ = _median_offset(store, plz, today, PRENOON_WINDOW[0], PRENOON_WINDOW[1])
    prenoon_dip = min(prenoon_dip, 0.0)  # vor 12 kann es nur runtergehen

    plan = DayPlan(name=name, emoji=emoji, current_price=current_price, market=market,
                   noon_jump_ct=noon_jump, noon_jump_n=jump_n, data_days=data_days,
                   favorite_label=favorite_label, cheapest_label=cheapest_label,
                   cheapest_price=cheapest_price)

    # Fenster aufbauen -------------------------------------------------------
    windows = [Window("jetzt", "jetzt", current_price, current_price, reachable=True)]

    if now_h < PRENOON_WINDOW[1]:
        low = current_price + prenoon_dip / 100.0  # kann nur fallen
        windows.append(Window("vor12", "kurz vor 12 Uhr", min(low, current_price),
                              current_price, reachable=True))

    if now_h < EVENING_END:
        ev = current_price + evening_off / 100.0
        spread = 0.010  # ±1 ct Bereich
        windows.append(Window("abend", "17–21 Uhr", ev - spread / 2, ev + spread / 2,
                              reachable=True))

    best_repr = min(w.repr_price for w in windows if w.reachable)
    for w in windows:
        w.score = _score(w.repr_price, best_repr, market, data_days)
    plan.windows = windows

    # Bestes ZUKUNFTS-Fenster (nicht "jetzt") --------------------------------
    future = [w for w in windows if w.name != "jetzt" and w.reachable]
    best_future = min(future, key=lambda w: w.repr_price) if future else None
    # Zielfenster für die Anzeige: bevorzugt ein Zukunftsfenster.
    plan.best = best_future if best_future is not None else min(windows, key=lambda w: w.repr_price)

    gain_ct = (current_price - best_future.repr_price) * 100 if best_future else 0.0

    # Empfehlung -------------------------------------------------------------
    if best_future and gain_ct >= 1.5:
        plan.recommendation = "WARTEN"
        gain_str = f"{gain_ct:.1f}".replace(".", ",")
        plan.action_line = (
            f"Bis {best_future.label_time} warten – erwartet ~{gain_str} ct günstiger."
        )
    else:
        plan.recommendation = "TANKEN"
        plan.action_line = "Jetzt tanken ist ok – kein nennenswert günstigeres Fenster erwartet."

    # Begründungen -----------------------------------------------------------
    if market.delta_ct is not None:
        plan.reasons.append(f"Favorit {market.label} (von {market.n_open} offenen Stationen).")
    if now_h < 12.0:
        plan.reasons.append(
            f"12-Uhr-Sprung erwartet: ~{noon_jump:.0f} ct – nach 12 Uhr wird es teurer."
        )
        plan.reasons.append("Vor 12 Uhr kann der Preis gesetzlich nicht steigen.")
    else:
        plan.reasons.append("Nach 12 Uhr sind nur noch Senkungen erlaubt – abends oft am günstigsten.")
    if evening_off <= -1.0:
        off_str = f"{abs(evening_off):.1f}".replace(".", ",")
        plan.reasons.append(
            f"An vergleichbaren Tagen abends im Schnitt {off_str} ct unter Vormittag."
        )

    detour = plan.detour_ct
    if detour is not None and detour >= 2.0:
        d_str = f"{detour:.1f}".replace(".", ",")
        saving_str = f"{detour * 0.5:.2f}".replace(".", ",")
        plan.reasons.append(
            f"Umweg zur günstigsten spart {d_str} ct/l (bei 50 l rund {saving_str} €)."
        )
    return plan
