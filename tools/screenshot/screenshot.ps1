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
  pwsh tools/screenshot/screenshot.ps1 -Name integrations-accounts,management-pack-details-overview
  Updates two screenshots. Separate the names with commas, without spaces.

.EXAMPLE
  pwsh tools/screenshot/screenshot.ps1 -Inspect "Management pack Configs" -Name management-pack-details-content
  For a new shot: describes the elements that show the text, after the steps of that shot: frame, element,
  row, expanders, and a suggested step.

.EXAMPLE
  pwsh tools/screenshot/screenshot.ps1 -Name adapter-instance-advanced-settings -SaveSteps $env:TEMP\shots
  Updates one screenshot, and saves a full-window screenshot after every step, to see what each step did.
#>
# No positional binding: a stray argument must fail, not land on -Credential and wait at a hidden password prompt.
[CmdletBinding(PositionalBinding = $false)]
param(
    [string[]]$Name,
    [switch]$List,
    [string]$SaveSteps,
    # Describe the elements that show this text, instead of taking screenshots. With -Page, or -Name and one shot.
    [string]$Inspect,
    # With -Inspect: the page to open, from the instance's root.
    [string]$Page,
    [string]$Url,
    [pscredential]$Credential,
    [string]$SecretFile = (Join-Path $PSScriptRoot '..\..\.secrets\vcf-ops.xml')
)

$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'screenshot.py'
$pyArgs = @()
# "a,b" in one argument, as pwsh -File passes a list, counts as two names.
foreach ($n in $Name -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }) { $pyArgs += '--name', $n }
if ($SaveSteps) { $pyArgs += '--save-steps', $SaveSteps }
if ($Inspect) { $pyArgs += '--inspect', $Inspect }
if ($Page) { $pyArgs += '--page', $Page }

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
    python -u $script @pyArgs
    $code = $LASTEXITCODE
} finally {
    Remove-Item Env:OPS_URL, Env:OPS_USER, Env:OPS_PASSWORD -ErrorAction SilentlyContinue
}
exit $code
