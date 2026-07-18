"""Schlagzeilen bewerten: eine Kernaussage + „vorher tanken vs. warten".

Zwei Wege:
1. Mit ANTHROPIC_API_KEY: Claude Haiku fasst die relevanteste Meldung in einem
   Satz zusammen und schätzt die Preistendenz ein (geringe Kosten).
2. Ohne Key: kostenlose Stichwort-Heuristik als Rückfallebene.

`advice` bedeutet:
- "vorher_tanken": Preise dürften steigen -> lieber heute vollmachen.
- "kann_warten":   Preise dürften fallen  -> Tanken kann warten.
- "neutral":       kein klares Signal.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .news import Headline

# Stichwörter für die Rückfall-Heuristik (klein geschrieben).
_BULLISH = [
    "steigt", "steigen", "steigend", "teurer", "anstieg", "höhere", "hoch",
    "kürzt", "kürzung", "förderkürzung", "drosselt", "sanktion", "embargo",
    "konflikt", "krieg", "angriff", "eskal", "ausfall", "knappheit", "engpass",
    "rekord", "verteuert",
]
_BEARISH = [
    "fällt", "fallen", "fallend", "günstiger", "billiger", "sinkt", "sinken",
    "rückgang", "gesunken", "nachfrage schwäch", "überangebot", "erhöht förder",
    "mehr öl", "entspann", "einigung", "waffenruhe", "verbilligt",
]

_SYSTEM = (
    "Du bist ein nüchterner Rohstoff-Analyst für den deutschen Tankstellenmarkt. "
    "Beurteile ausschließlich anhand der gegebenen Schlagzeilen, ob der Benzinpreis "
    "in den nächsten Tagen eher steigt, fällt oder stabil bleibt. Antworte knapp und "
    "auf Deutsch. Keine Spekulation über nicht genannte Ereignisse."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {
            "type": "string",
            "description": "Ein Satz zur preisrelevantesten Meldung (max. ~20 Wörter).",
        },
        "tendency": {"type": "string", "enum": ["steigend", "fallend", "stabil"]},
        "advice": {"type": "string", "enum": ["vorher_tanken", "kann_warten", "neutral"]},
        "reason": {"type": "string", "description": "Kurzbegründung, max. ein Satz."},
    },
    "required": ["headline", "tendency", "advice", "reason"],
    "additionalProperties": False,
}


@dataclass
class NewsInsight:
    headline: str
    tendency: str  # steigend | fallend | stabil
    advice: str    # vorher_tanken | kann_warten | neutral
    reason: str
    source: str    # "llm" | "heuristik"


def _tendency_to_advice(tendency: str) -> str:
    return {"steigend": "vorher_tanken", "fallend": "kann_warten"}.get(tendency, "neutral")


def analyze_with_llm(headlines: list[Headline], model: str, api_key: str) -> NewsInsight:
    import anthropic

    joined = "\n".join(f"- {h.title}" for h in headlines)
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=400,
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    "Schlagzeilen der letzten Tage:\n"
                    f"{joined}\n\n"
                    "Fasse die für den Benzinpreis wichtigste Meldung in einem Satz zusammen "
                    "und schätze die Tendenz ein."
                ),
            }
        ],
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    )
    text = next(b.text for b in resp.content if b.type == "text")
    data = json.loads(text)
    return NewsInsight(
        headline=data["headline"].strip(),
        tendency=data["tendency"],
        advice=data["advice"],
        reason=data["reason"].strip(),
        source="llm",
    )


def analyze_with_heuristic(headlines: list[Headline]) -> NewsInsight:
    bull = bear = 0
    hit_title = None
    for h in headlines:
        t = h.title.casefold()
        b = sum(1 for kw in _BULLISH if kw in t)
        s = sum(1 for kw in _BEARISH if kw in t)
        bull += b
        bear += s
        if hit_title is None and (b or s):
            hit_title = h.title

    if bull > bear:
        tendency = "steigend"
    elif bear > bull:
        tendency = "fallend"
    else:
        tendency = "stabil"

    headline = hit_title or (headlines[0].title if headlines else "Keine relevanten Meldungen.")
    return NewsInsight(
        headline=headline.strip(),
        tendency=tendency,
        advice=_tendency_to_advice(tendency),
        reason="Automatische Einschätzung nach Stichwörtern.",
        source="heuristik",
    )


def analyze(headlines: list[Headline], model: str, api_key: str | None) -> NewsInsight | None:
    """Beste verfügbare Analyse; None nur wenn gar keine Schlagzeilen vorliegen."""
    if not headlines:
        return None
    if api_key:
        try:
            return analyze_with_llm(headlines, model, api_key)
        except Exception:
            pass  # LLM-Fehler -> auf Heuristik zurückfallen
    return analyze_with_heuristic(headlines)
