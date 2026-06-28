@echo off
REM ============================================================
REM  PB POS — LOCAL silent auto-print (no Print dialog)
REM ============================================================
REM  BEFORE running:
REM    1. python manage.py runserver
REM    2. Set "BlackCopper 80mm" (or your kitchen printer) as DEFAULT
REM  IMPORTANT: Close ALL Chrome/Edge windows first, then run this.
REM ============================================================

set "POS_URL=http://127.0.0.1:8000/pos/?kiosk=1"
set "PROFILE=%LOCALAPPDATA%\PB-POS-Kiosk"

if not exist "%PROFILE%" mkdir "%PROFILE%"

set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
set "CHROME86=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
set "EDGE64=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"

REM Chrome flags required for silent print (no preview dialog):
REM   --kiosk              full-screen POS mode (required with kiosk-printing)
REM   --kiosk-printing     send straight to default printer
REM   --disable-print-preview
REM   --user-data-dir      separate profile so flags always apply

set "FLAGS=--user-data-dir=%PROFILE% --kiosk --kiosk-printing --disable-print-preview --no-first-run --disable-session-crashed-bubble --disable-infobars"

echo.
echo  PB POS local kiosk printing
echo  URL: %POS_URL%
echo  Profile: %PROFILE%
echo.
echo  Press Ctrl+C here, then Alt+F4 in browser to exit kiosk mode.
echo.

if exist "%CHROME%" (
    start "" "%CHROME%" %FLAGS% "%POS_URL%"
    exit /b 0
)
if exist "%CHROME86%" (
    start "" "%CHROME86%" %FLAGS% "%POS_URL%"
    exit /b 0
)
if exist "%EDGE64%" (
    start "" "%EDGE64%" %FLAGS% "%POS_URL%"
    exit /b 0
)
if exist "%EDGE%" (
    start "" "%EDGE%" %FLAGS% "%POS_URL%"
    exit /b 0
)

echo ERROR: Chrome or Edge not found. Install Google Chrome.
pause
exit /b 1
