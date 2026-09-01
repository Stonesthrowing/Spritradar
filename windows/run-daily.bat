@echo off
REM Sendet die tägliche Telegram-Nachricht (Windows Task Scheduler, z. B. 07:30).
REM Beim Doppelklick bleibt das Fenster bei Fehlern offen. Im Task Scheduler
REM als Argument  quiet  angeben: dann laeuft es lautlos und schreibt ins Log.
setlocal
cd /d "%~dp0.."
if not exist logs mkdir logs
set "LOG=logs\spritradar.log"
echo [%date% %time%] daily : Start>> "%LOG%"

if not exist "%~dp0secrets.bat" (
  echo [%date% %time%] daily : FEHLER - windows\secrets.bat fehlt>> "%LOG%"
  echo [FEHLER] windows\secrets.bat fehlt.
  echo          Loesung:  copy windows\secrets.example.bat windows\secrets.bat
  echo          danach die Keys darin eintragen.
  if not "%~1"=="quiet" pause
  exit /b 1
)
call "%~dp0secrets.bat"

if not exist ".venv\Scripts\python.exe" (
  echo [%date% %time%] daily : FEHLER - .venv fehlt>> "%LOG%"
  echo [FEHLER] Python-Umgebung fehlt.  Loesung:  py -m venv .venv
  if not "%~1"=="quiet" pause
  exit /b 1
)

REM FORCE nur beim Doppelklick (Test): dann wird sofort gesendet, egal welche
REM Uhrzeit. Der geplante Task ("quiet") laeuft OHNE FORCE und haelt sich an
REM Sendefenster + Tages-Dedup aus config.json - so gibt es keine zweite
REM Nachricht, falls parallel noch der GitHub-Zeitplan aktiv ist.
if "%~1"=="quiet" (
  ".venv\Scripts\python.exe" -m spritradar.main>> "%LOG%" 2>&1
) else (
  set FORCE=1
  ".venv\Scripts\python.exe" -m spritradar.main
)

if errorlevel 1 (
  echo [%date% %time%] daily : FEHLER beim Senden>> "%LOG%"
  echo.
  echo [FEHLER] Lauf fehlgeschlagen - siehe Meldung oben bzw. logs\spritradar.log
  echo          Bei "No module named ...":
  echo          .venv\Scripts\python.exe -m pip install -r requirements.txt
  if not "%~1"=="quiet" pause
  exit /b 1
)
echo [%date% %time%] daily : OK - Nachricht gesendet>> "%LOG%"
