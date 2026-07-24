@echo off
REM Stündliche Preis-Momentaufnahme (Windows Task Scheduler, z. B. jede Stunde).
cd /d "%~dp0.."
call "%~dp0secrets.bat"
".venv\Scripts\python.exe" -m spritradar.collect
