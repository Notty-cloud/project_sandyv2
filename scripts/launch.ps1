# Launch Project Sandy — Django API (port 3000) + Vite frontend (port 5173)
#
# Usage (from project root or anywhere):
#   .\scripts\launch.ps1
#   .\scripts\launch.ps1 -Migrate
#   .\scripts\launch.ps1 -NoBrowser
#
param(
    [switch]$Migrate,
    [switch]$NoBrowser,
    [switch]$Install
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

function Write-Step($message) {
    Write-Host "`n==> $message" -ForegroundColor Cyan
}

function Test-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Get-PythonCommand {
    $venvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
    if (Test-Path $venvPython) { return $venvPython }
    return "python"
}

Set-Location $ProjectRoot

Write-Host ""
Write-Host "  Project Sandy — Launch" -ForegroundColor Green
Write-Host "  $ProjectRoot"
Write-Host ""

if (-not (Test-Command "python")) {
    throw "Python not found. Install Python 3 and ensure it is on your PATH."
}
if (-not (Test-Command "npm")) {
    throw "npm not found. Install Node.js 16+ and ensure npm is on your PATH."
}

$python = Get-PythonCommand
Write-Step "Using Python: $python"

if ($Migrate) {
    Write-Step "Applying database migrations"
    & $python manage.py migrate --noinput
}

if ($Install -or -not (Test-Path (Join-Path $ProjectRoot "node_modules"))) {
    Write-Step "Installing frontend dependencies (npm install)"
    npm install
}

$backendCmd = @"
Set-Location '$ProjectRoot'
`$host.UI.RawUI.WindowTitle = 'Project Sandy — Django API (:3000)'
Write-Host 'Starting Django on http://localhost:3000' -ForegroundColor Green
& '$python' manage.py runserver 3000
"@

$frontendCmd = @"
Set-Location '$ProjectRoot'
`$host.UI.RawUI.WindowTitle = 'Project Sandy — Vite (:5173)'
Write-Host 'Starting Vite on http://localhost:5173' -ForegroundColor Green
npm run dev
"@

Write-Step "Starting Django API in a new terminal (port 3000)"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Start-Sleep -Seconds 2

Write-Step "Starting Vite frontend in a new terminal (port 5173)"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

if (-not $NoBrowser) {
    Write-Step "Opening http://localhost:5173"
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:5173"
}

Write-Host ""
Write-Host "  Both servers are starting in separate windows." -ForegroundColor Green
Write-Host "  Frontend : http://localhost:5173"
Write-Host "  API      : http://localhost:3000/api/"
Write-Host ""
Write-Host "  Tip: run with -Migrate to apply DB migrations first."
Write-Host "       run with -NoBrowser to skip opening the browser."
Write-Host ""
