@echo off
:: Intellog Quick Push Script
:: Usage: push.bat "commit message"
:: If no message given, uses timestamp

setlocal enabledelayedexpansion

:: Get commit message
if "%~1"=="" (
    for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set D=%%c-%%a-%%b
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do set T=%%a:%%b
    set MSG=update !D! !T!
) else (
    set MSG=%~1
)

echo.
echo ========================================
echo   INTELLOG - Git Push
echo ========================================
echo.

:: Stage all changes
echo [1/3] Staging changes...
git add -A

:: Show what changed
echo.
echo [Changed files:]
git diff --cached --stat
echo.

:: Commit
echo [2/3] Committing: %MSG%
git commit -m "%MSG%"

:: Push
echo.
echo [3/3] Pushing to GitHub...
git push origin main

echo.
echo ========================================
echo   Push complete!
echo   GitHub Actions CI will run automatically.
echo ========================================
echo.

endlocal
