# One-time: configure ngrok with your free authtoken, then start tunnel
# Get token: https://dashboard.ngrok.com/get-started/your-authtoken
param(
    [Parameter(Mandatory = $true)]
    [string]$AuthToken
)

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
ngrok config add-authtoken $AuthToken
Write-Host "Token saved. Starting tunnel on port 8000..."
Write-Host "Then open http://127.0.0.1:4040 for the public https URL"
ngrok http 8000
