@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\launch.ps1"
if %ERRORLEVEL% neq 0 pause
