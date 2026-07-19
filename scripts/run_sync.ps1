# Trigger full ads sync (requires backend + CRON_SECRET)
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$CronSecret = ""
)

if (-not $CronSecret) {
    $envPath = "D:\CODREAL\backend\.env"
    if (Test-Path $envPath) {
        Get-Content $envPath | ForEach-Object {
            if ($_ -match '^\s*CRON_SECRET=(.+)$') { $CronSecret = $Matches[1].Trim() }
        }
    }
}
if (-not $CronSecret) { $CronSecret = "codreal-dev-cron-secret" }

Write-Host "POST $BaseUrl/api/v1/jobs/sync-ads"
$headers = @{ Authorization = "Bearer $CronSecret" }
try {
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/v1/jobs/sync-ads" -Method POST -Headers $headers
    $r | ConvertTo-Json -Depth 6
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message }
}
