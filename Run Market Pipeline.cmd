@echo off
setlocal
title European Market Intelligence - Local Pipeline
cd /d "%~dp0"
echo European Market Intelligence
echo ============================
echo.
echo This window fetches public data, builds the database, and checks the results.
echo Internet access is required. Keep this window open until it finishes.
echo.
if not exist ".venv\Scripts\python.exe" (
    echo Python environment not found. Follow the Windows setup in README.md first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -X utf8 -m src.pipeline --config config/project.yml
if errorlevel 1 (
    echo.
    echo The pipeline failed. Read the error above for the reason.
    pause
    exit /b 1
)
echo.
".venv\Scripts\python.exe" -X utf8 -m src.show_results
if errorlevel 1 (
    echo The pipeline finished, but the result preview could not be displayed.
    pause
    exit /b 1
)
echo.
echo Open the data folder to view sample_market_intelligence.csv in Excel.
echo You can close this window when you have finished reading.
pause
