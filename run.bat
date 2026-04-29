@echo off
REM PyMon Startup Script - Windows
REM Usage: run.bat [port]

setlocal EnableDelayedExpansion

set PORT=%1
if "%PORT%"=="" set PORT=8090

echo ========================================
echo PyMon Server - Windows Edition
echo ========================================

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python 3.10+ from https://python.org
    exit /b 1
)

where pip >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: pip not found!
    exit /b 1
)

REM Create virtual environment
if not exist ".venv" (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
)

REM Install dependencies
echo [2/3] Installing dependencies...
call .venv\Scripts\pip.exe install --upgrade pip -q
call .venv\Scripts\pip.exe install -r requirements.txt -q

REM Run
echo [3/3] Starting server on port %PORT%...
echo Dashboard: http://localhost:%PORT%/dashboard/
echo.

call .venv\Scripts\python.exe -m pymon server --port %PORT%