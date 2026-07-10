"""Hilfsskript: Telegram-Chat-ID herausfinden.

Ablauf:
1. Dem Bot in Telegram einmalig schreiben (z. B. /start).
2. Dieses Skript ausführen (lokal oder via Workflow "Get Telegram Chat ID").
3. Angezeigte Chat-ID als GitHub-Secret TELEGRAM_CHAT_ID hinterlegen.
"""

from __future__ import annotations

import os
import sys

from . import telegram


def run() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("TELEGRAM_BOT_TOKEN fehlt.", file=sys.stderr)
        return 1

    ids = telegram.discover_chat_ids(token)
    if not ids:
        print(
            "Keine Chats gefunden. Schreibe dem Bot zuerst eine Nachricht "
            "(öffne t.me/<dein_bot> und sende /start), dann erneut ausführen."
        )
        return 2

    print("Gefundene Chat-IDs:", ids)
    print(f"-> Nutze diese als GitHub-Secret TELEGRAM_CHAT_ID: {ids[-1]}")

    # Bestätigung senden, damit klar ist, welcher Chat es ist.
    for cid in ids:
        try:
            telegram.send_message(
                token,
                cid,
                f"✅ Spritradar verbunden. Deine Chat-ID ist {cid}.\n"
                "Trag sie als Secret TELEGRAM_CHAT_ID ein.",
            )
        except Exception as exc:
            print(f"Konnte Chat {cid} nicht anschreiben: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
