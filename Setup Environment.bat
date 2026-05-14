@echo off
setlocal
cd /d "%~dp0"

echo Setting up the Construction Contact Database app environment...
echo.

if exist ".venv\Scripts\python.exe" (
    echo Existing Python environment found at .venv.
) else (
    echo Creating Python environment at .venv...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo The Windows Python launcher did not work. Trying python directly...
        python -m venv .venv
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Could not create .venv\Scripts\python.exe.
    echo Install Python 3.11 or newer, then run this launcher again.
    pause
    exit /b 1
)

echo Installing app requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Requirement installation failed. Check the messages above.
    pause
    exit /b 1
)

echo.
echo Setup complete.
echo You can now run "Load Planning Workbook.bat" or "Start App.bat".
pause
