@echo off
REM "Graphs"-Poller: beantwortet neue Telegram-Nachrichten (Task Scheduler, alle 2 Min).
REM Im Task Scheduler als Argument  quiet  angeben.
cd /d "%~dp0.."

if not exist "%~dp0secrets.bat" (
  echo [FEHLER] windows\secrets.bat fehlt - siehe windows\README.md.
  if "%~1"=="" pause
  exit /b 1
)
call "%~dp0secrets.bat"

if not exist ".venv\Scripts\python.exe" (
  echo [FEHLER] Python-Umgebung fehlt. Loesung:  py -m venv .venv
  if "%~1"=="" pause
  exit /b 1
)

".venv\Scripts\python.exe" -m spritradar.bot
if errorlevel 1 (
  echo.
  echo [FEHLER] Bei "No module named ...":
  echo          .venv\Scripts\python.exe -m pip install -r requirements.txt
  if "%~1"=="" pause
  exit /b 1
)
