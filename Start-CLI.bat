@echo off
title APZX G3NNNN - CLI
setlocal enabledelayedexpansion

:: Check if Python is available
where python >nul 2>&1 && set PY_CMD=python || set PY_CMD=py
if "!PY_CMD!" == "" (
    echo.
    echo   [ERROR] Python is not installed or not in PATH!
    echo   Please install Python 3.10+ from https://python.org
    echo   Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

:: Check if requirements are installed
echo.
echo   [APZX] Checking dependencies...
!PY_CMD! -c "import stealth_requests, colorama, websocket, primp" 2>nul
if errorlevel 1 (
    echo.
    echo   [APZX] Dependencies not found. Installing now...
    echo   [APZX] This may take a moment...
    echo.
    !PY_CMD! -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo   [ERROR] Failed to install dependencies!
        echo   Try running: !PY_CMD! -m pip install --user -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo.
    echo   [OK] Dependencies installed successfully!
    echo.
) else (
    echo   [OK] Dependencies already installed.
)

:: Run the CLI
echo.
echo   [APZX] Starting APZX G3NNNN CLI...
echo.
set APZX_FORCE_CLI=1
!PY_CMD! start.py %*
if errorlevel 1 (
    echo.
    echo   [ERROR] An error occurred. Press any key to exit.
    pause >nul
)
