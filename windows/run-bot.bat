@echo off
REM "Graphs"-Poller: beantwortet neue Telegram-Nachrichten (Task Scheduler, kurzer Intervall).
cd /d "%~dp0.."
call "%~dp0secrets.bat"
".venv\Scripts\python.exe" -m spritradar.bot
