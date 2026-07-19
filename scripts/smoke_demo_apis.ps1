# Smoke-test all APIs needed for local demo (no Meta/TikTok App IDs required)
$Base = if ($env:CODREAL_API) { $env:CODREAL_API } else { "http://127.0.0.1:8000" }
$ErrorActionPreference = "Continue"
$fail = 0

function Test-Api($Name, $Method, $Url, $Body = $null, $File = $null) {
    Write-Host "`n==> $Name" -ForegroundColor Cyan
    Write-Host "    $Method $Url"
    try {
        if ($File) {
            $r = Invoke-RestMethod -Uri $Url -Method $Method -Form @{ file = Get-Item $File }
        } elseif ($Body) {
            $r = Invoke-RestMethod -Uri $Url -Method $Method -ContentType "application/json" -Body $Body
        } else {
            $r = Invoke-RestMethod -Uri $Url -Method $Method
        }
        Write-Host "    OK" -ForegroundColor Green
        return $r
    } catch {
        Write-Host "    FAIL: $($_.Exception.Message)" -ForegroundColor Red
        script:fail++
        return $null
    }
}

Write-Host "CODReal demo API smoke test → $Base" -ForegroundColor Yellow

$h = Test-Api "Health" "GET" "$Base/api/v1/health"
if ($h) { Write-Host "    supabase=$($h.supabase_configured) meta=$($h.meta_configured) tiktok=$($h.tiktok_configured)" }

$ready = Test-Api "Demo ready" "GET" "$Base/api/v1/demo/ready"
if ($ready) {
    Write-Host "    instant_demo=$($ready.paths.instant_demo_no_login.ready)"
    Write-Host "    full_demo_account=$($ready.paths.full_demo_with_account.ready)"
}

$run = Test-Api "Demo run (match+KPIs)" "POST" "$Base/api/v1/demo/run"
if ($run) {
    Write-Host "    match_rate=$($run.matching.stats.match_rate) net_profit=$($run.kpis.net_profit) alerts=$($run.alerts.Count)"
}

$pipePath = "D:\CODREAL\samples\demo_pipeline.json"
if (Test-Path $pipePath) {
    $json = Get-Content $pipePath -Raw
    $p = Test-Api "Dashboard pipeline" "POST" "$Base/api/v1/dashboard/pipeline" $json
    if ($p) { Write-Host "    campaigns=$($p.kpis.total_campaigns) roas=$($p.kpis.real_roas)" }
}

$csv = "D:\CODREAL\samples\codreal_delivery_template.csv"
if (Test-Path $csv) {
    Write-Host "`n==> CSV upload (parse only)" -ForegroundColor Cyan
    try {
        # Windows PowerShell 5 has no -Form; use curl.exe multipart
        $raw = & curl.exe -s -X POST "$Base/api/v1/orders/upload" -F "file=@$csv"
        $u = $raw | ConvertFrom-Json
        if ($null -eq $u.valid_count) { throw "Unexpected response: $raw" }
        Write-Host "    OK valid=$($u.valid_count) errors=$($u.error_count)" -ForegroundColor Green
    } catch {
        Write-Host "    FAIL: $($_.Exception.Message)" -ForegroundColor Red
        $fail++
    }
}

Test-Api "Orders template" "GET" "$Base/api/v1/orders/template/info" | Out-Null
Test-Api "Auth status" "GET" "$Base/api/v1/auth/status" | Out-Null
Test-Api "Meta status" "GET" "$Base/api/v1/integrations/meta/status" | Out-Null
Test-Api "TikTok status" "GET" "$Base/api/v1/integrations/tiktok/status" | Out-Null
Test-Api "Matching run" "POST" "$Base/api/v1/matching/run" '{"orders":[{"id":"o1","phone":"0612345678","status":"delivered","amount_collected":100}],"leads":[{"id":"l1","campaign_id":"c1","phone":"+212612345678"}]}' | Out-Null

Write-Host "`n==============================" -ForegroundColor Yellow
if ($fail -eq 0) {
    Write-Host "ALL DEMO APIs OK — open http://localhost:3000/dashboard" -ForegroundColor Green
} else {
    Write-Host "$fail check(s) failed — is the API running from backend/ ?" -ForegroundColor Red
    exit 1
}
