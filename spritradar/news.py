"""Nachrichten-Schlagzeilen mit Bezug zum Spritpreis holen.

Quelle: Google-News-RSS – kostenlos, ohne API-Key. Wir fragen deutschsprachige
Treffer zu Benzin-/Öl-/OPEC-Themen der letzten Tage ab.
"""

from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests

RSS_BASE = "https://news.google.com/rss/search"


@dataclass
class Headline:
    title: str
    source: str
    published: str


def fetch_headlines(query: str, max_headlines: int = 8, timeout: int = 15) -> list[Headline]:
    """Aktuelle Schlagzeilen zur Query (deutsch), neueste zuerst."""
    q = urllib.parse.quote(f"{query} when:2d")
    url = f"{RSS_BASE}?q={q}&hl=de&gl=DE&ceid=DE:de"
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Spritradar/0.1"})
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    headlines: list[Headline] = []
    for item in root.iterfind(".//item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        source_el = item.find("source")
        source = (source_el.text or "").strip() if source_el is not None else ""
        published = (item.findtext("pubDate") or "").strip()
        headlines.append(Headline(title=title, source=source, published=published))
        if len(headlines) >= max_headlines:
            break
    return headlines
