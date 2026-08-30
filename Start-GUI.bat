@echo off
title APZX G3NNNN - GUI
setlocal enabledelayedexpansion

where python >nul 2>&1 && set PY_CMD=python || set PY_CMD=py
if "!PY_CMD!" == "" (
    echo.
    echo   [ERROR] Python is not installed or not in PATH!
    echo   Please install Python 3.10+ from https://python.org
    echo.
    pause
    exit /b 1
)

!PY_CMD! -c "import stealth_requests, colorama, websocket, primp, flask" 2>nul
if errorlevel 1 (
    !PY_CMD! -m pip install -r requirements.txt 2>nul
)

!PY_CMD! -c "import webview" 2>nul
if errorlevel 1 (
    !PY_CMD! -m pip install pywebview 2>nul
)

set APZX_FORCE_GUI=1
!PY_CMD! start.py %*

if errorlevel 1 (
    pause >nul
)
