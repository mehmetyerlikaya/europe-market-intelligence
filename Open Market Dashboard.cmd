@echo off
setlocal
title European Market Intelligence - Dashboard
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Complete the Windows setup in README.md first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo Install the dashboard first: .venv\Scripts\python.exe -m pip install -e ".[app]"
    pause
    exit /b 1
)
echo Opening http://127.0.0.1:8501
".venv\Scripts\python.exe" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=2)" >nul 2>&1
if not errorlevel 1 (
    start "" "http://127.0.0.1:8501"
    exit /b 0
)
echo Keep this window open while using the dashboard. Press Ctrl+C to stop it.
".venv\Scripts\python.exe" -m streamlit run streamlit_app.py --server.headless false --server.address 127.0.0.1
if errorlevel 1 pause
