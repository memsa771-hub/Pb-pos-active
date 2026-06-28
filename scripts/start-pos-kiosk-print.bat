@echo off
REM Production POS — silent auto-print (no Print dialog)
REM Set kitchen printer as DEFAULT, close all Chrome windows, then run.

set "POS_URL=https://rev1.pbpos.online/pos/?kiosk=1"
if not "%~1"=="" set "POS_URL=%~1"

set "PROFILE=%LOCALAPPDATA%\PB-POS-Kiosk"
if not exist "%PROFILE%" mkdir "%PROFILE%"

set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
set "CHROME86=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
set "EDGE64=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"

set "FLAGS=--user-data-dir=%PROFILE% --kiosk --kiosk-printing --disable-print-preview --no-first-run --disable-session-crashed-bubble --disable-infobars"

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

echo Could not find Chrome or Edge.
pause
exit /b 1
