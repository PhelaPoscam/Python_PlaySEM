# Pre-push checks for Python_PlaySEM (PowerShell)
# Usage: ./scripts/prepush.ps1

param(
    [switch]$Fix
)

Write-Host "Running pre-push checks..." -ForegroundColor Cyan

$python = "D:/TUNI/Python/Python_PlaySEM/.venv/Scripts/python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Python venv not found. Please activate venv first." -ForegroundColor Red
    exit 1
}

# 1) Black formatting
if ($Fix) {
    & $python -m pip show black | Out-Null
    if ($LASTEXITCODE -ne 0) { & $python -m pip install -q black }
    & $python -m black playsem tests
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    & $python -m pip show black | Out-Null
    if ($LASTEXITCODE -ne 0) { & $python -m pip install -q black }
    & $python -m black --check playsem tests
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Black failed. Re-run with -Fix to auto-format: ./scripts/prepush.ps1 -Fix" -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
}

# 2) Quick tests
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "All pre-push checks passed." -ForegroundColor Green
exit 0
