#Requires -Version 7
<#
.SYNOPSIS
  Take the documentation screenshots defined in screenshots.json from a VCF Operations instance.

.DESCRIPTION
  Reads the URL and login from .secrets/vcf-ops.xml (or -Url/-Credential/-SecretFile) and runs
  screenshot.py, which drives the installed Chrome in the background with Playwright. The login is
  passed to Python in this process's environment only, never on the command line.

  Shots only look at the instance: they open pages and expand sections, and never save anything.
  Exits 0 when every shot was saved, 1 otherwise.

.EXAMPLE
  pwsh tools/screenshot/screenshot.ps1
  Updates every screenshot.

.EXAMPLE
  pwsh tools/screenshot/screenshot.ps1 -Name adapter-instance-advanced-settings -SaveSteps $env:TEMP\shots
  Updates one screenshot, and saves a full-window screenshot after every step, to see what each step did.
#>
[CmdletBinding()]
param(
    [string[]]$Name,
    [switch]$List,
    [string]$SaveSteps,
    [string]$Url,
    [pscredential]$Credential,
    [string]$SecretFile = (Join-Path $PSScriptRoot '..\..\.secrets\vcf-ops.xml')
)

$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'screenshot.py'
$pyArgs = @()
foreach ($n in $Name) { $pyArgs += '--name', $n }
if ($SaveSteps) { $pyArgs += '--save-steps', $SaveSteps }

if ($List) {
    python $script --list
    exit $LASTEXITCODE
}

if ((-not $Url -or -not $Credential) -and (Test-Path $SecretFile)) {
    $secret = Import-Clixml $SecretFile
    if (-not $Url) { $Url = $secret.Url }
    if (-not $Credential) { $Credential = $secret.Credential }
}
if (-not $Url -or -not $Credential) {
    throw "No URL/credential. Pass -Url and -Credential, or create $SecretFile (see tools/validate/validate.md)."
}

python -c "import playwright" 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Playwright is not installed: python -m pip install --user playwright' }

try {
    $env:OPS_URL = $Url
    $env:OPS_USER = $Credential.UserName
    $env:OPS_PASSWORD = $Credential.GetNetworkCredential().Password
    python $script @pyArgs
    $code = $LASTEXITCODE
} finally {
    Remove-Item Env:OPS_URL, Env:OPS_USER, Env:OPS_PASSWORD -ErrorAction SilentlyContinue
}
exit $code
