@echo off
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title Advisor Review Platform

echo ==============================================
echo      Advisor Review Search Platform
echo ==============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %%PY_VER%%

:: Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)
for /f "tokens=1 delims=v" %%v in ('node --version 2^>^&1') do set NODE_VER=%%v
echo [OK] Node.js %%NODE_VER%%

echo.

:: Check backend deps
echo [..] Checking backend Python deps...
cd /d "%~dp0backend"
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [!!] Backend deps not installed. Installing...
    pip install -r requirements.txt -q
    if errorlevel 1 (
        echo [ERROR] Backend deps install failed.
        pause
        exit /b 1
    )
    echo [OK] Backend deps installed
) else (
    echo [OK] Backend deps ready
)

:: Check frontend deps
echo [..] Checking frontend Node deps...
cd /d "%~dp0frontend"
if not exist "node_modules\" (
    echo [!!] node_modules not found. Running npm install...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
    echo [OK] npm install done
) else (
    echo [OK] Frontend deps ready
)

echo.
echo ----------------------------------------------
echo   Starting services...
echo ----------------------------------------------

:: Start backend
start "Advisor-Backend" /d "%~dp0backend" cmd /k "title Backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: Wait
echo [..] Waiting for backend (5s)...
timeout /t 5 /nobreak >nul

:: Start frontend
start "Advisor-Frontend" /d "%~dp0frontend" cmd /k "title Frontend && npm run dev"

echo.
echo ==============================================
echo   Services starting...
echo   Backend : http://localhost:8000
echo   Frontend: http://localhost:5173
echo   API Docs: http://localhost:8000/docs
echo ==============================================
echo.
echo Close this window. Other windows keep running.
echo Press any key to close...
pause >nul
