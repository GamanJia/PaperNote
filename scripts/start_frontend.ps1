$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..\frontend")

if (-not $env:FRONTEND_HOST) { $env:FRONTEND_HOST = "127.0.0.1" }
if (-not $env:FRONTEND_PORT) { $env:FRONTEND_PORT = "5173" }

npm run dev -- --host $env:FRONTEND_HOST --port $env:FRONTEND_PORT --strictPort
