"""Lokaler Marktkontext: Ist der Favorit wirklich günstig – oder nur der ganze
Markt gerade billig/teuer?

Nutzt alle offenen Stationen im Umkreis (aus der Tankerkönig-Umkreissuche), um
Median und Perzentil zu bestimmen. So lässt sich der Favoritenpreis einordnen.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from .tankerkoenig import Station


@dataclass
class MarketContext:
    n_open: int
    median: float | None
    cheapest: float | None
    favorite_price: float | None
    delta_ct: float | None      # Favorit − Median, in ct (negativ = günstiger als Markt)
    pct_cheaper_than: float | None  # Anteil offener Stationen, die teurer sind (0..1)

    @property
    def label(self) -> str:
        if self.delta_ct is None:
            return "kein Marktvergleich verfügbar"
        d = abs(self.delta_ct)
        if self.delta_ct <= -0.5:
            return f"{d:.1f} ct unter lokalem Median".replace(".", ",")
        if self.delta_ct >= 0.5:
            return f"{d:.1f} ct über lokalem Median".replace(".", ",")
        return "auf Höhe des lokalen Medians"


def market_context(stations: list[Station], favorite_price: float | None) -> MarketContext:
    prices = [s.price for s in stations if s.price and s.price > 0]
    if not prices:
        return MarketContext(0, None, None, favorite_price, None, None)

    median = statistics.median(prices)
    cheapest = min(prices)
    delta = pct = None
    if favorite_price is not None:
        delta = round((favorite_price - median) * 100, 1)
        more_expensive = sum(1 for p in prices if p > favorite_price)
        pct = more_expensive / len(prices)
    return MarketContext(
        n_open=len(prices),
        median=median,
        cheapest=cheapest,
        favorite_price=favorite_price,
        delta_ct=delta,
        pct_cheaper_than=pct,
    )
