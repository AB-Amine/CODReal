# Start CODReal API — works from any directory
$Backend = Join-Path $PSScriptRoot "..\backend" | Resolve-Path
Set-Location $Backend

$Python = Join-Path $Backend ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "ERROR: venv not found at $Python" -ForegroundColor Red
    Write-Host "Run: cd backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt"
    exit 1
}

Write-Host "Working directory: $Backend" -ForegroundColor Cyan
Write-Host "Starting http://127.0.0.1:8000 ..." -ForegroundColor Cyan
& $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
