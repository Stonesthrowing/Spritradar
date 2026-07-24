@echo off
REM Sendet die tägliche Telegram-Nachricht (vom Windows Task Scheduler um 07:30 aufgerufen).
cd /d "%~dp0.."
call "%~dp0secrets.bat"
set FORCE=1
".venv\Scripts\python.exe" -m spritradar.main
