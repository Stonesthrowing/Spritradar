"""Bewertung: Wie gut ist heute zum E10-Kaufen? (1–10)

Ansatz v1 – transparent und erklärbar statt Blackbox:
Wir vergleichen den heutigen günstigsten Morgenpreis mit den günstigsten
Morgenpreisen der letzten Tage (immer zur gleichen Tageszeit gemessen, damit
der Vergleich fair ist). Liegt der heutige Preis niedrig im Vergleich zum
jüngsten Verlauf -> hoher Score. Liegt er hoch -> niedriger Score (lieber warten).

Der Score misst also *relativ* zum jüngsten Niveau, nicht absolut. Das ist
genau das Signal, das die Frage "lohnt sich heute?" beantwortet.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Score:
    value: int | None          # 1..10, oder None wenn zu wenig Historie
    today_price: float
    n_history: int
    avg: float | None
    minimum: float | None
    maximum: float | None
    pct_cheaper: float | None  # Anteil der Verlaufstage, die teurer/gleich waren

    @property
    def label(self) -> str:
        if self.value is None:
            return "noch keine Bewertung"
        if self.value >= 8:
            return "sehr guter Tag zum Tanken"
        if self.value >= 6:
            return "guter Tag"
        if self.value >= 4:
            return "durchschnittlich"
        return "eher teuer – wenn möglich warten"

    @property
    def recommendation(self) -> str:
        if self.value is None:
            return "❔"
        if self.value >= 6:
            return "✅ kaufen"
        if self.value >= 4:
            return "➖ ok / nur wenn nötig"
        return "🛑 lieber warten"


def score_today(today_price: float, history: list[float], min_history: int) -> Score:
    n = len(history)
    if n == 0:
        return Score(None, today_price, 0, None, None, None, None)

    avg = sum(history) / n
    minimum = min(history)
    maximum = max(history)

    if n < min_history:
        return Score(None, today_price, n, avg, minimum, maximum, None)

    # Anteil der Verlaufstage, die >= heutiger Preis waren (heute also
    # gleich günstig oder günstiger). 1.0 = heute so günstig wie nie zuletzt.
    cheaper_or_equal = sum(1 for p in history if p >= today_price)
    pct = cheaper_or_equal / n

    value = round(1 + 9 * pct)
    value = max(1, min(10, value))

    return Score(value, today_price, n, avg, minimum, maximum, pct)
