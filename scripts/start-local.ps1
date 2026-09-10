$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$dockerExecutable = if ($dockerCommand) { $dockerCommand.Source } else { $null }
if (-not $dockerExecutable) {
    $dockerExecutable = @(
        "$env:LOCALAPPDATA/Programs/DockerDesktop/resources/bin/docker.exe",
        "$env:ProgramFiles/Docker/Docker/resources/bin/docker.exe"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $dockerExecutable) { throw 'Docker Desktop with Compose is required. Install it, then run this script again.' }
& $dockerExecutable info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker engine is unavailable. Open Docker Desktop and resolve its startup warning, then retry.' }
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
& $dockerExecutable compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose configuration failed' }
& $dockerExecutable compose up --build -d --wait --wait-timeout 300
if ($LASTEXITCODE -ne 0) { throw 'Startup failed; inspect docker compose ps and docker compose logs' }
$hmiBinding = & $dockerExecutable compose port operator-hmi 80
if ($LASTEXITCODE -ne 0) { throw 'Could not resolve the HMI port' }
$hmiPort = ($hmiBinding -split ':')[-1]
Write-Host "LIVE HMI: http://localhost:$hmiPort/?missionId=MSN-LIVE-001"
