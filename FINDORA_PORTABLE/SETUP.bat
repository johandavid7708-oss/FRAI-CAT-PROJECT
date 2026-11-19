@echo off
setlocal
cd /d "%~dp0"
title Findora Portable - Setup
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\prepare.ps1"
if errorlevel 1 (
 echo.
 echo SETUP FAILED. Please keep this window and send the error above.
 pause
 exit /b 1
)
echo.
echo SETUP COMPLETE. Use START.bat to launch Findora.
pause
