@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "APP_DB=%~dp0construction_platform.sqlite3"

if not exist "%PYTHON_EXE%" (
    echo Python environment not found.
    echo Run "Setup Environment.bat" first, then run this launcher again.
    pause
    exit /b 1
)

echo Starting Construction Contact Database app...
echo Database:
echo "%APP_DB%"
echo.
"%PYTHON_EXE%" app.py --db "%APP_DB%" run
if errorlevel 1 (
    echo.
    echo App exited with an error. Check the messages above.
    pause
    exit /b 1
)
