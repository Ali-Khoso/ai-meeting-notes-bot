@echo off
cd /d "%~dp0"
if not exist .env copy .env.example .env >nul
py -3 -m app.server
pause
