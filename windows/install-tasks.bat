@echo off
REM ===========================================================================
REM  Spritradar - Einrichtung auf dem Mini-PC. Einfach doppelklicken.
REM
REM  Legt die beiden geplanten Aufgaben an:
REM    "Spritradar Bot"      alle 2 Minuten  -> hoert auf "go" / "graphs"
REM    "Spritradar Collect"  stuendlich      -> stille Preis-Momentaufnahme
REM
REM  Eine taegliche Nachricht gibt es nicht mehr - der Tankplan kommt nur noch
REM  auf "go" im Telegram-Chat.
REM ===========================================================================
setlocal
cd /d "%~dp0.."

echo ============================================================
echo  SPRITRADAR - AUFGABEN EINRICHTEN
echo ============================================================
echo.
echo Ordner: %CD%
echo.

REM --- 1. secrets.bat -------------------------------------------------------
if not exist "%~dp0secrets.bat" (
  echo [FEHLER] windows\secrets.bat fehlt.
  echo.
  echo   So anlegen:
  echo     copy windows\secrets.example.bat windows\secrets.bat
  echo     notepad windows\secrets.bat
  echo   Danach Keys eintragen, speichern und dieses Skript erneut starten.
  echo.
  pause
  exit /b 1
)
echo [ok] windows\secrets.bat gefunden.

REM --- 2. Python-Umgebung ---------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
  echo [..] Python-Umgebung fehlt - wird angelegt ...
  py -m venv .venv
  if errorlevel 1 (
    echo.
    echo [FEHLER] "py -m venv .venv" ist fehlgeschlagen.
    echo          Ist Python installiert?  Test:  py --version
    echo          Download: https://www.python.org/downloads/
    echo          Beim Installer "Add python.exe to PATH" ankreuzen.
    echo.
    pause
    exit /b 1
  )
)
echo [ok] Python-Umgebung .venv vorhanden.

echo [..] Abhaengigkeiten installieren (dauert beim ersten Mal etwas) ...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
if errorlevel 1 (
  echo.
  echo [FEHLER] Installation der Abhaengigkeiten fehlgeschlagen.
  echo          Manuell versuchen:
  echo          .venv\Scripts\python.exe -m pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)
echo [ok] Abhaengigkeiten installiert.
echo.

REM --- 3. Alte Tagesaufgabe entfernen --------------------------------------
schtasks /Query /TN "Spritradar Daily" >nul 2>&1
if not errorlevel 1 (
  echo [..] Alte Aufgabe "Spritradar Daily" entfernen ^(es gibt keine
  echo      taegliche Nachricht mehr^) ...
  schtasks /Delete /TN "Spritradar Daily" /F >nul 2>&1
  echo [ok] entfernt.
)

REM --- 4. Aufgaben anlegen --------------------------------------------------
echo [..] Aufgabe "Spritradar Bot" anlegen ^(alle 2 Minuten^) ...
schtasks /Create /F /TN "Spritradar Bot" /TR "\"%~dp0run-bot.bat\" quiet" /SC MINUTE /MO 2
if errorlevel 1 goto taskfail

echo [..] Aufgabe "Spritradar Collect" anlegen ^(stuendlich^) ...
schtasks /Create /F /TN "Spritradar Collect" /TR "\"%~dp0run-collect.bat\" quiet" /SC HOURLY
if errorlevel 1 goto taskfail

echo.
echo ============================================================
echo  FERTIG
echo ============================================================
echo.
echo  Schreib deinem Bot jetzt in Telegram:   go
echo  Die Antwort sollte innerhalb von ~2 Minuten kommen.
echo.
echo  "graphs" liefert die drei Tagesverlauf-Charts.
echo.
echo  Kontrolle spaeter:  windows\status.bat doppelklicken.
echo.
echo  Hinweis: Die Aufgaben laufen, solange dieser Benutzer angemeldet
echo  ist. Der Mini-PC sollte also angemeldet durchlaufen.
echo.
pause
exit /b 0

:taskfail
echo.
echo [FEHLER] Aufgabe konnte nicht angelegt werden.
echo          Versuch: dieses Skript per Rechtsklick
echo          "Als Administrator ausfuehren" starten.
echo.
pause
exit /b 1
