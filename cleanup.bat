@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\cleanup_space.ps1"
set "cleanup_result=%errorlevel%"
echo.
if not defined CODEX_NO_PAUSE pause
exit /b %cleanup_result%
