"""Konfiguration und Secrets laden.

Standorte / Fenster kommen aus config.json (im Repo, kein Geheimnis).
API-Keys kommen ausschließlich aus Umgebungsvariablen (GitHub-Secrets),
niemals aus dem Code oder dem Repo.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config.json"
DEFAULT_HISTORY_PATH = REPO_ROOT / "data" / "history.json"


@dataclass
class PreferredSpec:
    """Feste Wunsch-Tankstelle, erkannt über Marke/Straße/Ort statt über ID."""

    label: str
    brand: str = ""
    street: str = ""
    house_number: str = ""
    place: str = ""


@dataclass
class Location:
    name: str
    plz: str
    lat: float
    lng: float
    radius_km: float
    emoji: str = "⛽"
    preferred: list[PreferredSpec] = field(default_factory=list)


@dataclass
class Config:
    fuel_type: str = "e10"
    timezone: str = "Europe/Berlin"
    history_window_days: int = 14
    min_history_for_score: int = 4
    send_window_local_hours: tuple[int, int] = (7, 10)
    locations: list[Location] = field(default_factory=list)


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> Config:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    locations = []
    for loc in data.get("locations", []):
        preferred = [
            PreferredSpec(
                label=p.get("label") or p.get("brand", "Bevorzugt"),
                brand=p.get("brand", ""),
                street=p.get("street", ""),
                house_number=str(p.get("house_number", "")),
                place=p.get("place", ""),
            )
            for p in loc.get("preferred", [])
        ]
        locations.append(
            Location(
                name=loc["name"],
                plz=str(loc["plz"]),
                lat=float(loc["lat"]),
                lng=float(loc["lng"]),
                radius_km=float(loc.get("radius_km", 4.0)),
                emoji=loc.get("emoji", "⛽"),
                preferred=preferred,
            )
        )
    window = data.get("send_window_local_hours", [7, 10])
    return Config(
        fuel_type=data.get("fuel_type", "e10"),
        timezone=data.get("timezone", "Europe/Berlin"),
        history_window_days=int(data.get("history_window_days", 14)),
        min_history_for_score=int(data.get("min_history_for_score", 4)),
        send_window_local_hours=(int(window[0]), int(window[1])),
        locations=locations,
    )


@dataclass
class Secrets:
    tankerkoenig_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str | None


def load_secrets() -> Secrets:
    api_key = os.environ.get("TANKERKOENIG_API_KEY", "").strip()
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or None
    if not api_key:
        raise RuntimeError("TANKERKOENIG_API_KEY ist nicht gesetzt (GitHub-Secret fehlt).")
    if not bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN ist nicht gesetzt (GitHub-Secret fehlt).")
    return Secrets(api_key, bot_token, chat_id)
