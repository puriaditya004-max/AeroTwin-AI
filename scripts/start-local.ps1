$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker Desktop with Compose v2 is required. Install/start it, then run this script again.' }
if (-not (Test-Path -LiteralPath '.env')) {
    $demoDbPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
    $demoJwtSecret = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(48))
    @"
POSTGRES_USER=aerotwin
POSTGRES_PASSWORD=$demoDbPassword
POSTGRES_DB=aerotwin
JWT_SECRET=$demoJwtSecret
APP_MODE=local-demo
ENABLE_DEMO_AUTH=true
VITE_HMI_MODE=LIVE
M1_DEFAULT_SCENARIO=normal
M1_DEFAULT_MISSION_ID=MSN-LIVE-001
M5_ALLOW_EXPERIMENTAL_FALLBACK=true
M6_RUL_CRITICAL_LOWER_BOUND=50
M6_RUL_HIGH_CYCLES=100
M6_RUL_MEDIUM_CYCLES=200
"@ | Set-Content -LiteralPath '.env' -Encoding utf8
}
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose configuration failed' }
docker compose up --build -d --wait --wait-timeout 300
if ($LASTEXITCODE -ne 0) { throw 'Startup failed; inspect docker compose ps and docker compose logs' }
Write-Host 'LIVE HMI: http://localhost:5173/?missionId=MSN-LIVE-001'
