$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..\backend")

if (-not $env:BACKEND_HOST) { $env:BACKEND_HOST = "127.0.0.1" }
if (-not $env:BACKEND_PORT) { $env:BACKEND_PORT = "8000" }

uvicorn app.main:app --reload --host $env:BACKEND_HOST --port $env:BACKEND_PORT
