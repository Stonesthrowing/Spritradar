@echo off
REM Zeigt auf einen Blick, ob die geplanten Aufgaben existieren, wann sie zuletzt
REM liefen und was zuletzt im Log stand. Einfach doppelklicken.
setlocal
cd /d "%~dp0.."
echo ============================================================
echo  SPRITRADAR - STATUS
echo ============================================================
echo.
echo --- Geplante Aufgaben ------------------------------------
for %%T in ("Spritradar Daily" "Spritradar Collect" "Spritradar Bot") do (
  schtasks /Query /TN %%T /FO LIST /V >nul 2>&1
  if errorlevel 1 (
    echo   %%T : NICHT ANGELEGT  ^<-- deshalb laeuft nichts automatisch
  ) else (
    echo   %%T :
    schtasks /Query /TN %%T /FO LIST /V | findstr /I /C:"Status" /C:"Letzte Laufzeit" /C:"Naechste Laufzeit" /C:"Nächste Laufzeit" /C:"Letztes Ergebnis" /C:"Last Run Time" /C:"Next Run Time" /C:"Last Result"
  )
  echo.
)

echo --- Voraussetzungen --------------------------------------
if exist "windows\secrets.bat" (echo   secrets.bat            : vorhanden) else (echo   secrets.bat            : FEHLT)
if exist ".venv\Scripts\python.exe" (echo   Python-Umgebung .venv  : vorhanden) else (echo   Python-Umgebung .venv  : FEHLT)
echo.

echo --- Letzte Log-Eintraege ---------------------------------
if exist "logs\spritradar.log" (
  powershell -NoProfile -Command "Get-Content 'logs\spritradar.log' -Tail 25"
) else (
  echo   Noch kein Log vorhanden - es lief also noch kein Lauf mit dem neuen Stand.
)
echo.
echo ============================================================
pause
