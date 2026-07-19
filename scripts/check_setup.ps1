# CODReal setup checker
$ErrorActionPreference = "Continue"
Write-Host "=== CODReal setup check ===" -ForegroundColor Cyan

$backendEnv = "D:\CODREAL\backend\.env"
$frontEnv = "D:\CODREAL\frontend\.env.local"

function Get-EnvMap($path) {
    $map = @{}
    if (-not (Test-Path $path)) { return $map }
    Get-Content $path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $i = $line.IndexOf("=")
            $k = $line.Substring(0, $i).Trim()
            $v = $line.Substring($i + 1).Trim()
            $map[$k] = $v
        }
    }
    return $map
}

function Test-Key($map, $key, $placeholder) {
    if (-not $map.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($map[$key])) {
        return "MISSING"
    }
    $v = $map[$key]
    foreach ($p in $placeholder) {
        if ($v -eq $p -or $v.Contains("YOUR_PROJECT") -or $v.Contains("your-")) {
            return "PLACEHOLDER"
        }
    }
    return "OK"
}

$be = Get-EnvMap $backendEnv
$fe = Get-EnvMap $frontEnv

Write-Host "`n[Backend .env]"
if (-not (Test-Path $backendEnv)) { Write-Host "  FILE MISSING" -ForegroundColor Red }
else {
    $checks = @(
        @("SUPABASE_URL", @("https://YOUR_PROJECT.supabase.co")),
        @("SUPABASE_KEY", @("your-service-role-key")),
        @("SUPABASE_JWT_SECRET", @("your-jwt-secret")),
        @("META_APP_ID", @("")),
        @("TIKTOK_APP_ID", @("")),
        @("CRON_SECRET", @("change-me-to-a-long-random-cron-secret", "codreal-dev-cron-secret"))
    )
    foreach ($c in $checks) {
        $st = Test-Key $be $c[0] $c[1]
        $color = if ($st -eq "OK") { "Green" } elseif ($st -eq "PLACEHOLDER") { "Yellow" } else { "Red" }
        # Empty META/TIKTOK is optional
        if (($c[0] -eq "META_APP_ID" -or $c[0] -eq "TIKTOK_APP_ID") -and $st -ne "OK") {
            $st = "OPTIONAL (empty = use mock)"
            $color = "DarkGray"
        }
        Write-Host ("  {0,-22} {1}" -f $c[0], $st) -ForegroundColor $color
    }
}

Write-Host "`n[Frontend .env.local]"
if (-not (Test-Path $frontEnv)) { Write-Host "  FILE MISSING" -ForegroundColor Red }
else {
    foreach ($c in @(
        @("NEXT_PUBLIC_API_URL", @()),
        @("NEXT_PUBLIC_SUPABASE_URL", @("https://YOUR_PROJECT.supabase.co")),
        @("NEXT_PUBLIC_SUPABASE_ANON_KEY", @("your-anon-public-key", "your-anon-key"))
    )) {
        $st = Test-Key $fe $c[0] $c[1]
        if ($c[0] -eq "NEXT_PUBLIC_API_URL" -and $st -eq "OK") { }
        elseif ($c[0] -eq "NEXT_PUBLIC_API_URL" -and $st -eq "MISSING") {
            $st = "MISSING (defaults to localhost:8000)"
        }
        $color = if ($st -eq "OK") { "Green" } elseif ($st -match "OPTIONAL|defaults") { "DarkGray" } elseif ($st -eq "PLACEHOLDER") { "Yellow" } else { "Red" }
        Write-Host ("  {0,-32} {1}" -f $c[0], $st) -ForegroundColor $color
    }
}

Write-Host "`n[Live API]"
try {
    $h = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 3
    Write-Host "  API online: $($h.app) v$($h.version)" -ForegroundColor Green
    Write-Host "  supabase_configured: $($h.supabase_configured)"
    Write-Host "  meta_configured: $($h.meta_configured)"
    Write-Host "  tiktok_configured: $($h.tiktok_configured)"
} catch {
    Write-Host "  API offline — start backend first" -ForegroundColor Yellow
}

Write-Host "`nNext: fill keys from docs/YOU_MUST_PROVIDE.md then restart servers." -ForegroundColor Cyan
