@echo off
:: Intellog Full Startup Script
:: Starts: Backend + Cloudflare Tunnel + Auto-Deploy Watcher
:: Usage: start_all.bat

echo.
echo ========================================
echo   INTELLOG - Full System Startup
echo ========================================
echo.

:: Create logs directory
if not exist "logs" mkdir logs

:: Kill old processes first
echo [0/3] Cleaning up old processes...
taskkill /F /IM uvicorn.exe >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

:: Start Backend
echo [1/3] Starting FastAPI backend on :8000...
start /b cmd /c "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > logs\backend.log 2>&1"
timeout /t 3 /nobreak >nul
curl -s http://localhost:8000/api/health >nul 2>&1
if errorlevel 1 (
    echo      !! Backend failed to start. Check logs\backend.log
) else (
    echo      OK - Backend running
)

:: Start Cloudflare Tunnel
echo [2/3] Starting Cloudflare Tunnel (intellog.dev)...
start /b cmd /c "cloudflared tunnel run intellog > logs\tunnel.log 2>&1"
timeout /t 3 /nobreak >nul
echo      OK - Tunnel starting (may take ~10s to connect)

:: Start Auto-Deploy Watcher
echo [3/3] Starting Auto-Deploy Watcher...
start /b cmd /c "python autodeploy.py > logs\autodeploy.log 2>&1"
echo      OK - Watching GitHub for changes (60s interval)

echo.
echo ========================================
echo   All services started!
echo.
echo   Dashboard: https://intellog.dev
echo   Local:     http://localhost:8000
echo.
echo   Logs:
echo     Backend:    logs\backend.log
echo     Tunnel:     logs\tunnel.log
echo     AutoDeploy: logs\autodeploy.log
echo.
echo   Push code:  push.bat "message"
echo   Stop all:   stop_all.bat
echo ========================================
echo.
