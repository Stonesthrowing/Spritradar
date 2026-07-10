"""Telegram-Nachricht formatieren (deutsch, als Klartext).

Klartext bewusst gewählt: keine Markdown-/HTML-Escaping-Fallen bei Preisen
mit Komma/Punkt. Emojis funktionieren trotzdem.
"""

from __future__ import annotations

import datetime as dt

import holidays

from .scoring import Score

WEEKDAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def _euro(price: float) -> str:
    return f"{price:.3f}".replace(".", ",") + " €"


def _bar(value: int | None) -> str:
    if value is None:
        return "▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️"
    filled = "🟩" if value >= 6 else ("🟨" if value >= 4 else "🟥")
    return filled * value + "▫️" * (10 - value)


def build_message(
    now_local: dt.datetime,
    results: list[tuple[str, str, Score, str]],
) -> str:
    """results: Liste von (name, emoji, Score, günstigste-Tankstelle-Label)."""
    date_str = f"{WEEKDAYS_DE[now_local.weekday()]}, {now_local:%d.%m.%Y}"
    lines = [f"⛽ Spritradar – Super E10", date_str, ""]

    for name, emoji, sc, station in results:
        head = f"{emoji} {name}"
        if sc.value is None:
            lines.append(head)
            lines.append(f"   Günstigste: {_euro(sc.today_price)} – {station}")
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
            lines.append(f"   Günstigste: {_euro(sc.today_price)} – {station}")
            lines.append(
                f"   {sc.n_history}-Tage: Ø {_euro(sc.avg)} · "
                f"min {_euro(sc.minimum)} · max {_euro(sc.maximum)}"
            )
            if sc.pct_cheaper is not None:
                lines.append(
                    f"   → günstiger als an {round(sc.pct_cheaper * 100)}% der letzten Tage"
                )
        lines.append("")

    lines.append(_outlook_note(now_local))
    lines.append(
        "💡 Tipp: In DE ist Sprit abends (ca. 18–21 Uhr) meist am günstigsten – "
        "morgens ist Tageshoch. Der Score bewertet das *Tagesniveau*."
    )
    return "\n".join(lines).strip()


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
