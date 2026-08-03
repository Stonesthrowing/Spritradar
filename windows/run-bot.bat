@echo off
REM "Graphs"-Poller: beantwortet neue Telegram-Nachrichten (Task Scheduler, alle 2 Min).
REM Im Task Scheduler als Argument  quiet  angeben.
REM Laeuft sehr oft -> es werden nur Fehler protokolliert, damit das Log klein bleibt.
setlocal
cd /d "%~dp0.."
if not exist logs mkdir logs
set "LOG=logs\spritradar.log"

if not exist "%~dp0secrets.bat" (
  echo [%date% %time%] bot    : FEHLER - windows\secrets.bat fehlt>> "%LOG%"
  echo [FEHLER] windows\secrets.bat fehlt - siehe windows\README.md.
  if not "%~1"=="quiet" pause
  exit /b 1
)
call "%~dp0secrets.bat"

if not exist ".venv\Scripts\python.exe" (
  echo [%date% %time%] bot    : FEHLER - .venv fehlt>> "%LOG%"
  echo [FEHLER] Python-Umgebung fehlt. Loesung:  py -m venv .venv
  if not "%~1"=="quiet" pause
  exit /b 1
)

if "%~1"=="quiet" (
  ".venv\Scripts\python.exe" -m spritradar.bot> nul 2>> "%LOG%"
) else (
  ".venv\Scripts\python.exe" -m spritradar.bot
)

if errorlevel 1 (
  echo [%date% %time%] bot    : FEHLER>> "%LOG%"
  echo.
  echo [FEHLER] Bei "No module named ...":
  echo          .venv\Scripts\python.exe -m pip install -r requirements.txt
  if not "%~1"=="quiet" pause
  exit /b 1
)
