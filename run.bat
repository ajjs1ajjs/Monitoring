@echo off
rem PyMon NOC (Go) - run from source
if not exist pymon.exe (
    echo Building PyMon...
    go build -o pymon.exe .\cmd\pymon
    if errorlevel 1 exit /b 1
)
echo Starting PyMon...
pymon.exe server %*
