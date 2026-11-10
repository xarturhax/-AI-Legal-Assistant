@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\manage.ps1" setup
set "launch_result=%errorlevel%"
if not "%launch_result%"=="0" (
  echo.
  echo Установка завершилась с ошибкой. Подробности выше и в папке logs.
  if not defined CODEX_NO_PAUSE pause
)
exit /b %launch_result%
