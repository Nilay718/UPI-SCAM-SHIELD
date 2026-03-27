param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

function Get-FreePort([int]$p) {
  try {
    $c = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $c) { return $null }
    return $p
  } catch {
    return $p
  }
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"

if (-not (Test-Path $backend)) {
  throw "backend folder not found."
}

Push-Location $backend
try {
  if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creating venv..."
    python -m venv .venv
  }

  Write-Host "Installing dependencies..."
  .\.venv\Scripts\python -m pip install -r requirements.txt | Out-Null

  $free = Get-FreePort $Port
  if ($null -eq $free) {
    $free = Get-FreePort 8001
  }
  if ($null -eq $free) {
    $free = 8002
  }

  Write-Host ""
  Write-Host "UPI Scam Shield running:"
  Write-Host "Home     : http://127.0.0.1:$free/"
  Write-Host "Analyzer  : http://127.0.0.1:$free/analyzer"
  Write-Host "Demo Tour : http://127.0.0.1:$free/analyzer?demo=1"
  Write-Host ""
  Write-Host "Tip: Demo messages at demo_assets\DEMO_MESSAGES.md"
  Write-Host ""

  .\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port $free
} finally {
  Pop-Location
}

