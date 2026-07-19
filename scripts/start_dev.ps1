# Start backend + frontend (two windows)
$root = "D:\CODREAL"

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd $root\backend; .\.venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
)

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd $root\frontend; npm run dev"
)

Write-Host "Started API : http://127.0.0.1:8000/docs"
Write-Host "Started UI  : http://localhost:3000"
Write-Host "Checklist   : powershell -File $root\scripts\check_setup.ps1"
