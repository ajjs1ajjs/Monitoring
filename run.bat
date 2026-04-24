@echo off
REM PyMon Startup Script

cd /d "%~dp0"

echo Starting PyMon server...
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "pymon.db" (
    echo First run - installing dependencies...
    pip install -r requirements.txt
    pip install -e . --no-deps
)

REM Start server
python -m pymon.cli server --host 0.0.0.0 --port 8090

pause
