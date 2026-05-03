@echo off
:: Intellog Deploy Script
:: Pulls latest code from GitHub and restarts all services
:: Usage: deploy.bat

echo.
echo ========================================
echo   INTELLOG - Deploy
echo ========================================
echo.

:: Pull latest code
echo [1/4] Pulling latest from GitHub...
git pull origin main
if errorlevel 1 (
    echo ERROR: Git pull failed!
    pause
    exit /b 1
)

:: Install/update dependencies
echo.
echo [2/4] Updating dependencies...
pip install -r requirements.txt -q

:: Kill old processes
echo.
echo [3/4] Stopping old services...
taskkill /F /IM uvicorn.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

:: Start backend
echo.
echo [4/4] Starting services...
start /b cmd /c "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > logs\backend.log 2>&1"
timeout /t 3 /nobreak >nul

:: Verify
curl -s http://localhost:8000/api/health >nul 2>&1
if errorlevel 1 (
    echo WARNING: Backend health check failed. Check logs\backend.log
) else (
    echo Backend: OK (http://localhost:8000)
)

:: Check tunnel
tasklist /FI "IMAGENAME eq cloudflared.exe" 2>nul | findstr cloudflared >nul
if errorlevel 1 (
    echo.
    echo WARNING: Cloudflare tunnel not running!
    echo Start it with: cloudflared tunnel run intellog
) else (
    echo Tunnel: OK (intellog.dev)
)

echo.
echo ========================================
echo   Deploy complete!
echo   Live at: https://intellog.dev
echo ========================================
echo.
