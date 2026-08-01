@echo off
REM Sendet die tägliche Telegram-Nachricht (Windows Task Scheduler, z. B. 07:30).
REM Beim Doppelklick bleibt das Fenster bei Fehlern offen. Im Task Scheduler
REM als Argument  quiet  angeben, damit nichts auf eine Eingabe wartet.
cd /d "%~dp0.."

if not exist "%~dp0secrets.bat" (
  echo [FEHLER] windows\secrets.bat fehlt.
  echo          Loesung:  copy windows\secrets.example.bat windows\secrets.bat
  echo          danach die Keys darin eintragen.
  echo          Tipp: Wenn du die Datei mit Notepad angelegt hast, heisst sie
  echo          evtl. secrets.bat.txt - dann umbenennen.
  if "%~1"=="" pause
  exit /b 1
)
call "%~dp0secrets.bat"

if not exist ".venv\Scripts\python.exe" (
  echo [FEHLER] Python-Umgebung fehlt.
  echo          Loesung:  py -m venv .venv
  if "%~1"=="" pause
  exit /b 1
)

set FORCE=1
".venv\Scripts\python.exe" -m spritradar.main
if errorlevel 1 (
  echo.
  echo [FEHLER] Lauf fehlgeschlagen - siehe Meldung oben.
  echo          Bei "No module named ...":
  echo          .venv\Scripts\python.exe -m pip install -r requirements.txt
  if "%~1"=="" pause
  exit /b 1
)
