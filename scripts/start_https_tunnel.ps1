# Expose local API (port 8000) with free Cloudflare HTTPS tunnel
# Requires: API running on 127.0.0.1:8000 + cloudflared installed
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "Starting Cloudflare quick tunnel -> http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Copy the https://....trycloudflare.com URL, then update:" -ForegroundColor Yellow
Write-Host "  backend/.env  TIKTOK_REDIRECT_URI=https://YOUR-SUBDOMAIN.trycloudflare.com/api/v1/integrations/tiktok/callback"
Write-Host "  TikTok console Advertiser redirect URL = same value"
Write-Host "Restart the API after changing .env"
Write-Host ""

cloudflared tunnel --url http://127.0.0.1:8000
