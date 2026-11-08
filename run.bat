@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title Smart Job Hunter AI Agent
echo ========================================================
echo       Starting Smart Job Hunter AI Agent Dashboard
echo ========================================================
echo.
echo Opening browser at http://127.0.0.1:8080 ...
start http://127.0.0.1:8080
echo.
python main.py
pause
