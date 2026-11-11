param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($Port -lt 1 -or $Port -gt 65535) { throw 'Choose a port between 1 and 65535.' }
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Install the locked Python environment first; see README.md.' }
if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) { throw 'Build the frontend first with npm ci and npm run build in frontend.' }
Write-Host "Price Action Research Lab: http://127.0.0.1:$Port"
& '.venv/Scripts/python.exe' -m uvicorn backend.lab.api:create_app --factory --host 127.0.0.1 --port $Port --no-access-log
exit $LASTEXITCODE
