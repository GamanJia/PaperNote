@echo off
setlocal

cd /d "%~dp0\..\backend"

if "%BACKEND_HOST%"=="" set BACKEND_HOST=127.0.0.1
if "%BACKEND_PORT%"=="" set BACKEND_PORT=8000

uvicorn app.main:app --reload --host %BACKEND_HOST% --port %BACKEND_PORT%
