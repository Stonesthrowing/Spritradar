"""Telegram-Nachricht formatieren (deutsch, als Klartext).

Klartext bewusst gewählt: keine Markdown-/HTML-Escaping-Fallen bei Preisen
mit Komma/Punkt. Emojis funktionieren trotzdem.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import holidays

from .analysis import NewsInsight
from .config import DailyTips
from .plan import DayPlan, score_emoji
from .scoring import Score

WEEKDAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


@dataclass
class PreferredResult:
    label: str
    price: float | None            # None = heute keine Daten (geschlossen/außerhalb Radius)
    delta_to_cheapest: float | None  # in €, >0 = teurer als günstigste
    is_cheapest: bool = False


@dataclass
class LocationResult:
    name: str
    emoji: str
    score: Score
    cheapest_label: str
    preferred: list[PreferredResult] = field(default_factory=list)


def _euro(price: float) -> str:
    return f"{price:.3f}".replace(".", ",") + " €"


def _delta_ct(delta_eur: float) -> str:
    ct = delta_eur * 100
    return f"{ct:+.1f}".replace(".", ",") + " ct"


def _bar(value: int | None) -> str:
    if value is None:
        return "▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️"
    filled = "🟩" if value >= 6 else ("🟨" if value >= 4 else "🟥")
    return filled * value + "▫️" * (10 - value)


def build_message(
    now_local: dt.datetime,
    results: list[LocationResult],
    news: NewsInsight | None = None,
    daily_tips: DailyTips | None = None,
) -> str:
    date_str = f"{WEEKDAYS_DE[now_local.weekday()]}, {now_local:%d.%m.%Y}"
    lines = [f"⛽ Spritradar – Super E10", date_str, ""]

    for res in results:
        sc = res.score
        head = f"{res.emoji} {res.name}"
        if sc.value is None:
            lines.append(head)
            lines.append(f"   Günstigste: {_euro(sc.today_price)} – {res.cheapest_label}")
            if sc.n_history > 0:
                lines.append(
                    f"   Verlauf: Ø {_euro(sc.avg)} · min {_euro(sc.minimum)} "
                    f"(sammle noch Daten, Tag {sc.n_history + 1})"
                )
            else:
                lines.append("   (erster Messtag – ab morgen mit Bewertung)")
        else:
            lines.append(f"{head}:  {sc.value}/10  {sc.recommendation}")
            lines.append(f"   {_bar(sc.value)}")
            lines.append(f"   Günstigste: {_euro(sc.today_price)} – {res.cheapest_label}")
            lines.append(
                f"   {sc.n_history}-Tage: Ø {_euro(sc.avg)} · "
                f"min {_euro(sc.minimum)} · max {_euro(sc.maximum)}"
            )
            if sc.pct_cheaper is not None:
                lines.append(
                    f"   → günstiger als an {round(sc.pct_cheaper * 100)}% der letzten Tage"
                )

        for pref in res.preferred:
            lines.append(_preferred_line(pref))
        lines.append("")

    if news is not None:
        lines.append(_news_block(news))
        lines.append("")

    lines.append(_outlook_note(now_local))

    if daily_tips is not None:
        lines.append("")
        lines.append(
            f"(Beste Uhrzeit: {daily_tips.best_time} · "
            f"Bester Wochentag: {daily_tips.best_weekday})"
        )
    return "\n".join(lines).strip()


def _price_range(low: float, high: float) -> str:
    if abs(high - low) < 0.0005:
        return _euro(low)
    return f"{low:.3f}".replace(".", ",") + "–" + f"{high:.3f}".replace(".", ",") + " €"


def _window_line(label: str, low: float, high: float, score: int) -> str:
    return f"{label:<16} {_price_range(low, high)}   {score_emoji(score)} {score}/100"


def build_tankplan(
    now_local: dt.datetime,
    plans: list[DayPlan],
    news: NewsInsight | None = None,
) -> str:
    """Morgennachricht im 12-Uhr-Regime: Empfehlung + bestes Fenster je Station."""
    date_str = f"{WEEKDAYS_DE[now_local.weekday()]}, {now_local:%d.%m.%Y}"
    lines = [f"⛽ E10-Tankplan – {date_str}", f"Datenstand: {now_local:%H:%M} Uhr", ""]

    overall_wait = any(p.recommendation == "WARTEN" for p in plans)
    lines.append(f"EMPFEHLUNG: {'WARTEN' if overall_wait else 'JETZT TANKEN OK'}")
    if overall_wait:
        first = next(p for p in plans if p.recommendation == "WARTEN")
        if first.best is not None:
            lines.append(f"Günstigstes Fenster heute: {first.best.label_time}")
    lines.append("")

    for p in plans:
        lines.append(f"{p.emoji} {p.name}")
        for w in p.windows:
            disp = w.label_time[:1].upper() + w.label_time[1:]
            lines.append(_window_line(disp, w.price_low, w.price_high, w.score))
        lines.append(f"→ {p.action_line}")
        if p.reasons:
            lines.append("Warum:")
            for r in p.reasons:
                lines.append(f"• {r}")
        lines.append("")

    if news is not None:
        lines.append(_news_block(news))
        lines.append("")

    lines.append(_outlook_note(now_local))
    conf = ", ".join(sorted({p.confidence for p in plans})) if plans else "gering"
    hint = " (Daten werden noch gesammelt)" if plans and min(p.data_days for p in plans) < 14 else ""
    lines.append(f"Prognosesicherheit: {conf}{hint}")
    lines.append("Quelle: MTS-K via Tankerkönig, CC BY 4.0")
    return "\n".join(lines).strip()


def _news_block(news: NewsInsight) -> str:
    advice = {
        "vorher_tanken": "⛽ Eher heute vollmachen – Preise dürften anziehen.",
        "kann_warten": "⏳ Tanken kann warten – Preise dürften nachgeben.",
        "neutral": "➡️ Kein klares Preissignal.",
    }[news.advice]
    lines = [f"📰 {news.headline}", f"   {advice}"]
    if news.reason:
        lines.append(f"   ({news.reason})")
    return "\n".join(lines)


def _preferred_line(pref: PreferredResult) -> str:
    if pref.price is None:
        return f"   ⭐ {pref.label}: aktuell keine Daten (geschlossen?)"
    if pref.is_cheapest or (pref.delta_to_cheapest is not None and pref.delta_to_cheapest < 0.0005):
        return f"   ⭐ {pref.label}: {_euro(pref.price)} (= günstigste hier 👍)"
    return f"   ⭐ {pref.label}: {_euro(pref.price)} ({_delta_ct(pref.delta_to_cheapest)} teurer)"


def _outlook_note(now_local: dt.datetime) -> str:
    de_nrw = holidays.Germany(prov="NW", years=now_local.year)
    today = now_local.date()
    tomorrow = today + dt.timedelta(days=1)
    weekday = now_local.weekday()  # 0=Mo

    if today in de_nrw:
        return f"📌 Heute Feiertag ({de_nrw.get(today)}) – Nachfrage & Preise oft höher."
    if tomorrow in de_nrw:
        return "📌 Morgen Feiertag – Preise steigen erfahrungsgemäß vorher an. Heute tanken kann sich lohnen."
    if weekday == 4:  # Freitag
        return "📌 Freitag – vor dem Wochenende ziehen die Preise oft an."
    if weekday in (5, 6):  # Sa/So
        return "📌 Wochenende – tendenziell teurer als werktags Mitte der Woche."
    if weekday in (1, 2):  # Di/Mi
        return "📌 Wochenmitte – statistisch oft die günstigsten Tage."
    return "📌 Werktag – normales Preisniveau erwartet."
