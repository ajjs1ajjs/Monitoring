@echo off
REM PyMon - One Command Deploy (SQLite Version)
cd /d "%~dp0"

echo ========================================
echo PyMon - Starting...
echo ========================================

REM Check for Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Setup Virtual Environment if not exists
if not exist ".venv" (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
)

echo [2/3] Installing/Updating dependencies...
call .venv\Scripts\activate
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install -e . --no-deps -q

echo [3/3] Starting PyMon Server...
echo Dashboard: http://localhost:8090/dashboard/
python -m pymon server
pause
