@echo off
title Smart Flight Hunter AI - Cloud Access
cd /d "%~dp0"
echo ========================================================
echo   Starting Smart Flight Hunter AI (100%% Free Cloud)
echo ========================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_cloud.ps1"
pause
