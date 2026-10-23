#Requires -Version 7
<#
.SYNOPSIS
  Build the management pack (.pak) without any prompts.

.DESCRIPTION
  Runs the Integration SDK's mp-build on "Management Pack" through
  mp_build_headless.py, so it works where there is no Windows console. mp-build
  builds the adapter image, pushes it to the container registry, and assembles
  the pak into "Management Pack/build".

  Exits 0 and prints the pak path when a pak for the manifest version was made,
  1 otherwise.

.EXAMPLE
  pwsh tools/build/build.ps1
#>
[CmdletBinding()]
param(
    # Where the adapter image is pushed, and where VCF Operations pulls it from.
    [string]$Registry = 'ghcr.io/e1-rahabok/vcf-operations-vcommunity',
    # mp-build is stopped after this long. A hang usually means it is waiting on a prompt.
    [int]$TimeoutMinutes = 15
)

$ErrorActionPreference = 'Stop'
$project = Resolve-Path (Join-Path $PSScriptRoot '..\..\Management Pack')
$configFile = Join-Path $project 'config.json'
$version = (Get-Content (Join-Path $project 'manifest.txt') -Raw | ConvertFrom-Json).version

# --- Docker ------------------------------------------------------------------
docker info --format '{{.ServerVersion}}' *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'Docker is not answering. Start Docker Desktop and wait for "Engine running".'
}

# --- Registry ----------------------------------------------------------------
# mp-build prompts for a registry when config.json has none. config.json is
# gitignored, so a fresh clone always starts without one.
$config = (Test-Path $configFile) ?(Get-Content $configFile -Raw | ConvertFrom-Json -AsHashtable) : @{}
if ($config.container_repository -ne $Registry -or $config.container_push_repository -ne $Registry) {
    $config.container_repository = $Registry
    $config.container_push_repository = $Registry
    $config | ConvertTo-Json | Set-Content $configFile
    "Registry set to $Registry in config.json"
}

# --- Build -------------------------------------------------------------------
$started = Get-Date
$noInput = New-TemporaryFile
try {
    $proc = Start-Process python -NoNewWindow -PassThru -RedirectStandardInput $noInput `
        -ArgumentList @("`"$(Join-Path $PSScriptRoot 'mp_build_headless.py')`"", '-p', "`"$project`"")
    if (-not $proc.WaitForExit($TimeoutMinutes * 60 * 1000)) {
        $proc | Stop-Process -Force
        throw "mp-build did not finish in $TimeoutMinutes minutes. See 'Management Pack/logs/build.log'."
    }
} finally {
    Remove-Item $noInput -ErrorAction SilentlyContinue
}

# mp-build's exit code is not reliable, so check for the pak itself.
$pak = Get-ChildItem (Join-Path $project 'build') -Filter "*$version*.pak" -ErrorAction SilentlyContinue |
    Where-Object LastWriteTime -ge $started | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $pak) {
    Write-Error "No pak for version $version was built. See 'Management Pack/logs/build.log'." -ErrorAction Continue
    exit 1
}
"Built $($pak.FullName) ($([math]::Round($pak.Length / 1KB)) KB)"
