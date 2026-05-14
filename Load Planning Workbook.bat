@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "APP_DB=%~dp0construction_platform.sqlite3"
set "WORKBOOK=N:\Chris M\AI\Desktop Contact Database & Operating Platform..xlsx"

if not exist "%PYTHON_EXE%" (
    echo Python environment not found.
    echo Run "Setup Environment.bat" first, then run this launcher again.
    pause
    exit /b 1
)

if not exist "%WORKBOOK%" (
    echo Planning workbook not found:
    echo "%WORKBOOK%"
    pause
    exit /b 1
)

echo Loading planning workbook into:
echo "%APP_DB%"
echo.
"%PYTHON_EXE%" app.py --db "%APP_DB%" bootstrap-workbook "%WORKBOOK%"
if errorlevel 1 (
    echo.
    echo Workbook load failed. Check the messages above.
    pause
    exit /b 1
)

echo.
echo Workbook load complete. You can now run "Start App.bat".
pause
