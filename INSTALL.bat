@echo off
chcp 65001 >nul 2>&1
title TermiChat Installer

echo.
echo ========================================
echo    TermiChat Installer
echo ========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM ================================================
REM Step 1: Check Ollama
REM ================================================
echo [1/4] Checking Ollama...

where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Ollama not installed!
    echo Download at: https://ollama.com
    echo.
    pause
    exit /b 1
)
echo OK - Ollama found

REM ================================================
REM Step 2: Check Python dependencies
REM ================================================
echo.
echo [2/4] Checking Python...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Download at: https://python.org/downloads
    pause
    exit /b 1
)
echo OK - Python found

echo.
echo [3/4] Installing dependencies...
pip install ollama pygments pyperclip --quiet 2>nul
echo OK

REM ================================================
REM Step 4: Context Menu
REM ================================================
echo.
echo [4/4] Install Context Menu?
echo.
echo This adds "Chat with AI" to right-click menu
echo.

set /p INSTALL_MENU="Install context menu? (y/n): "
if /i "%INSTALL_MENU%"=="y" (
    echo.
    call :install_context
)

echo.
echo ========================================
echo    INSTALLATION COMPLETE!
echo ========================================
echo.
echo Run TermiChat:
echo   cd "%SCRIPT_DIR%"
echo   ai
echo.
echo Or double-click: ai.bat
echo.
pause
exit /b 0

:install_context
set "CC_BAT=%SCRIPT_DIR%\ai.bat"

reg add "HKCU\Software\Classes\Directory\shell\TermiChat" /ve /d "Chat with AI" /f >nul 2>&1
reg add "HKCU\Software\Classes\Directory\shell\TermiChat\command" /ve /d "\"%CC_BAT%\"" /f >nul 2>&1

reg add "HKCU\Software\Classes\Directory\Background\shell\TermiChat" /ve /d "Chat with AI Here" /f >nul 2>&1
reg add "HKCU\Software\Classes\Directory\Background\shell\TermiChat\command" /ve /d "\"%CC_BAT%\"" /f >nul 2>&1

echo Context menu installed!
echo   - Right-click folder: "Chat with AI"
echo   - Right-click empty area: "Chat with AI Here"
exit /b 0
