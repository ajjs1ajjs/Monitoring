@echo off
REM PyMon - One Command Deploy (Production Ready)
REM Usage: run.bat [-postgres] [-tls]

cd /d "%~dp0"

echo ========================================
echo PyMon - Starting...
echo ========================================

REM Find Python (works if in PATH or via py launcher)
set PYTHON=
where python >nul 2>&1
if %ERRORLEVEL% equ 0 set PYTHON=python
if defined PYTHON goto :run

py -3 --version >nul 2>&1
if %ERRORLEVEL% equ 0 set PYTHON=py\ -3
if defined PYTHON goto :run

REM Try common locations
if exist "C:\Python312\python.exe" set PYTHON=C:\Python312\python.exe
if exist "C:\Python311\python.exe" set PYTHON=C:\Python311\python.exe  
if exist "C:\Python310\python.exe" set PYTHON=C:\Python310\python.exe

:run
if not defined PYTHON (
    echo ERROR: Python not found. Install from https://python.org
    pause
    exit /b 1
)

REM Install deps if needed
echo [1/2] Checking dependencies...
%PYTHON% -m pip install -r requirements.txt 2>nul

REM Run
echo [2/2] Starting PyMon...
%PYTHON% -m pymon.cli server %*