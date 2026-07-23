@echo off
REM Kopiere diese Datei zu "secrets.bat" (im selben Ordner) und trage deine Werte ein.
REM secrets.bat wird NICHT eingecheckt (steht in .gitignore) – deine Keys bleiben lokal.

set TANKERKOENIG_API_KEY=dein-tankerkoenig-key
set TELEGRAM_BOT_TOKEN=dein-bot-token
set TELEGRAM_CHAT_ID=deine-chat-id
REM Optional (LLM-Nachrichtenanalyse); leer lassen = kostenlose Heuristik:
set ANTHROPIC_API_KEY=
