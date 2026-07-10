"""Telegram-Versand über die Bot-API."""

from __future__ import annotations

import requests

API = "https://api.telegram.org/bot{token}/{method}"


def _call(token: str, method: str, params: dict, timeout: int = 20) -> dict:
    resp = requests.post(API.format(token=token, method=method), json=params, timeout=timeout)
    data = resp.json()
    if not data.get("ok", False):
        raise RuntimeError(f"Telegram-Fehler bei {method}: {data.get('description')}")
    return data["result"]


def send_message(token: str, chat_id: str | int, text: str) -> dict:
    return _call(token, "sendMessage", {"chat_id": chat_id, "text": text})


def discover_chat_ids(token: str) -> list[int]:
    """Chat-IDs aus getUpdates (jeder, der dem Bot geschrieben hat)."""
    try:
        updates = _call(token, "getUpdates", {})
    except RuntimeError:
        return []
    seen: list[int] = []
    for u in updates:
        msg = u.get("message") or u.get("edited_message") or {}
        chat = msg.get("chat") or {}
        cid = chat.get("id")
        if cid is not None and cid not in seen:
            seen.append(cid)
    return seen


def resolve_chat_id(token: str, configured: str | None) -> str | None:
    """Konfigurierte Chat-ID nehmen, sonst automatisch die letzte aus getUpdates.

    Gibt zusätzlich einen Hinweis aus, damit die ID als Secret fixiert werden
    kann (getUpdates ist nur ein Fallback und kann leer laufen).
    """
    if configured:
        return configured
    ids = discover_chat_ids(token)
    if not ids:
        return None
    chosen = ids[-1]
    print(
        f"[Spritradar] Keine TELEGRAM_CHAT_ID gesetzt. Automatisch erkannt: {chosen}\n"
        f"             -> Bitte als GitHub-Secret TELEGRAM_CHAT_ID hinterlegen "
        f"(erkannte IDs: {ids})."
    )
    return str(chosen)
