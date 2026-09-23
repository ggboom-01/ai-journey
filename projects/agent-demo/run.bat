@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

if "%~1"=="" (
    python agent.py "现在几点了？顺便算一下 (1234*56)+789 等于多少"
) else (
    python agent.py %*
)
echo.
pause
