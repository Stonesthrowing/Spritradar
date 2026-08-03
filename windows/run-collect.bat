@echo off
REM Stündliche Preis-Momentaufnahme (Windows Task Scheduler, jede Stunde).
REM Im Task Scheduler als Argument  quiet  angeben.
setlocal
cd /d "%~dp0.."
if not exist logs mkdir logs
set "LOG=logs\spritradar.log"

if not exist "%~dp0secrets.bat" (
  echo [%date% %time%] collect: FEHLER - windows\secrets.bat fehlt>> "%LOG%"
  echo [FEHLER] windows\secrets.bat fehlt - siehe windows\README.md.
  if not "%~1"=="quiet" pause
  exit /b 1
)
call "%~dp0secrets.bat"

if not exist ".venv\Scripts\python.exe" (
  echo [%date% %time%] collect: FEHLER - .venv fehlt>> "%LOG%"
  echo [FEHLER] Python-Umgebung fehlt. Loesung:  py -m venv .venv
  if not "%~1"=="quiet" pause
  exit /b 1
)

if "%~1"=="quiet" (
  ".venv\Scripts\python.exe" -m spritradar.collect>> "%LOG%" 2>&1
) else (
  ".venv\Scripts\python.exe" -m spritradar.collect
)

if errorlevel 1 (
  echo [%date% %time%] collect: FEHLER>> "%LOG%"
  echo.
  echo [FEHLER] Bei "No module named ...":
  echo          .venv\Scripts\python.exe -m pip install -r requirements.txt
  if not "%~1"=="quiet" pause
  exit /b 1
)
echo [%date% %time%] collect: OK>> "%LOG%"
