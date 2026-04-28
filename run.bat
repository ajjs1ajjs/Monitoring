@echo off
REM PyMon Startup Script - Single command to install and run
REM Usage: run.bat              - Install deps + run with SQLite (default)
REM        run.bat postgres     - Install deps + run with PostgreSQL
REM        run.bat tls          - Install deps + run with TLS
REM        run.bat full         - Install deps + run with PostgreSQL + TLS

cd /d "%~dp0"

set MODE=%1

echo ========================================
echo PyMon Server - Installing & Running
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Install dependencies
echo [1/3] Installing dependencies...
pip install -r requirements.txt -q
pip install -e . --no-deps -q

REM Set defaults
set STORAGE=sqlite
set PG_DSN=
set TLS_ENABLED=false
set TLS_CERT=
set TLS_KEY=

REM Parse mode
if "%MODE%"=="postgres" (
    echo [2/3] PostgreSQL mode selected
    set STORAGE=postgres
    set PG_DSN=postgresql://user:password@localhost/pymon
    echo        Set PG_DSN env var for your PostgreSQL
) else if "%MODE%"=="tls" (
    echo [2/3] TLS mode selected
    set TLS_ENABLED=true
    set TLS_CERT=cert.pem
    set TLS_KEY=key.pem
    echo        Place cert.pem and key.pem in this folder
) else if "%MODE%"=="full" (
    echo [2/3] Full mode: PostgreSQL + TLS
    set STORAGE=postgres
    set PG_DSN=postgresql://user:password@localhost/pymon
    set TLS_ENABLED=true
    set TLS_CERT=cert.pem
    set TLS_KEY=key.pem
    echo        Set PG_DSN and place certs
) else (
    echo [2/3] SQLite mode (default)
)

echo [3/3] Starting server...
echo.

REM Run with selected backend
if "%STORAGE%"=="postgres" (
    if defined PG_DSN (
        python -m pymon.cli server --storage postgres --pg-dsn "%PG_DSN%"
    ) else (
        python -m pymon.cli server --storage postgres
    )
) else (
    python -m pymon.cli server
)

pause