@echo off
setlocal

cd /d "%~dp0\..\frontend"

if "%FRONTEND_HOST%"=="" set FRONTEND_HOST=127.0.0.1
if "%FRONTEND_PORT%"=="" set FRONTEND_PORT=5173

npm run dev -- --host %FRONTEND_HOST% --port %FRONTEND_PORT%
