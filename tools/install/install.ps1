#Requires -Version 7
<#
.SYNOPSIS
  Upload and install the management pack (.pak) on a VCF Operations instance.

.DESCRIPTION
  This CHANGES the instance: it replaces the installed version of the pack.

  The pak is unsigned. The admin API (CaSA) refuses unsigned paks on upload
  (pak_manager.pakfile.no_signature) and has no option to skip the check, so the
  upload and install go through the same UI requests as Administration >
  Integrations > Repository > Add, with signature checking ignored (see
  pak-install-requests.md). The install is then followed through CaSA's status
  call, which the UI's own status calls do not report reliably.

  Needs the local 'admin' account, and "Allow Unsigned PAK Installation" turned
  on in /admin > Administrator Settings > Security Settings.

  Exits 0 when the install completes, 1 otherwise.

.EXAMPLE
  pwsh tools/install/install.ps1
  Installs the pak in "Management Pack/build" for the manifest version.

.EXAMPLE
  pwsh tools/install/install.ps1 -Pak path/to/vCommunity_0.4.2.pak
#>
[CmdletBinding()]
param(
    [string]$Pak,
    [string]$Url,
    [pscredential]$Credential,
    [string]$SecretFile = (Join-Path $PSScriptRoot '..\..\.secrets\vcf-ops.xml'),
    [int]$TimeoutMinutes = 20
)

$ErrorActionPreference = 'Stop'

if ((-not $Url -or -not $Credential) -and (Test-Path $SecretFile)) {
    $secret = Import-Clixml $SecretFile
    if (-not $Url) { $Url = $secret.Url }
    if (-not $Credential) { $Credential = $secret.Credential }
}
if (-not $Url -or -not $Credential) {
    throw "No URL/credential. Pass -Url and -Credential, or create $SecretFile (see tools/validate/validate.md)."
}

if (-not $Pak) {
    $project = Join-Path $PSScriptRoot '..\..\Management Pack'
    $version = (Get-Content (Join-Path $project 'manifest.txt') -Raw | ConvertFrom-Json).version
    $Pak = (Get-ChildItem (Join-Path $project 'build') -Filter "*$version*.pak" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime | Select-Object -Last 1).FullName
    if (-not $Pak) { throw "No pak for version $version in 'Management Pack/build'. Run tools/build/build.ps1 first." }
}
$Pak = (Resolve-Path $Pak).Path

$root = $Url.TrimEnd('/')
$ui = "$root/ui"
$hostName = ([uri]$Url).Host
$clock = [Diagnostics.Stopwatch]::StartNew()

# Progress goes to the console as it happens; each step says what it is about to do.
function Write-Step([int]$Number, [string]$Text) {
    Write-Host ("[{0}/6] {1}" -f $Number, $Text) -ForegroundColor Cyan
}
function Write-Detail([string]$Text) {
    Write-Host ("      {0}  ({1:m\:ss})" -f $Text, $clock.Elapsed)
}

Write-Host "Installing $(Split-Path $Pak -Leaf) ($([math]::Round((Get-Item $Pak).Length / 1KB)) KB) on $hostName as $($Credential.UserName)"

# --- Admin API (CaSA): preflight and status ----------------------------------
$casaWeb = @{
    Credential = $Credential; Authentication = 'Basic'; SkipCertificateCheck = $true
    Headers = @{ Accept = 'application/json' }; TimeoutSec = 120
}
function Get-Casa([string]$Path) { Invoke-RestMethod -Uri "$root/casa/$Path" @casaWeb }

Write-Step 1 'Checking the instance is online and no other pak install is running'
$cluster = Get-Casa 'deployment/cluster/info'
if ($cluster.online_state -ne 'ONLINE') { throw "Cluster is $($cluster.online_state), not ONLINE." }
if ($cluster.is_pak_installation_active) { throw 'Another pak install is already running on the instance.' }
Write-Detail "Cluster '$($cluster.cluster_name)' is ONLINE and idle"

# --- UI login ----------------------------------------------------------------
Write-Step 2 'Logging in to the VCF Operations UI'
$session = [Microsoft.PowerShell.Commands.WebRequestSession]::new()
$web = @{ WebSession = $session; SkipCertificateCheck = $true; TimeoutSec = 600 }

Invoke-WebRequest "$ui/login.action?vcf=1" @web | Out-Null
$login = Invoke-WebRequest -Method Post "$ui/login.action" @web -Body @{
    mainAction = 'login'; userName = $Credential.UserName; password = $Credential.GetNetworkCredential().Password
    authSourceId = 'localItem'; authSourceName = 'Local Account'; authSourceType = ''
    forceLogin = 'false'; timezone = '0'; languageCode = 'us'
}
if ($login.Content.Trim() -ne 'ok') { throw "UI login failed: $($login.Content.Trim())" }

# The CSRF token is in the OPS_SESSION cookie set by index.action (path
# /vcf-operations, so not returned for /ui URLs). Following its redirect
# invalidates that cookie, so don't; the unfollowed redirect is reported as a
# non-terminating error, hence SilentlyContinue.
Invoke-WebRequest "$ui/index.action" @web -MaximumRedirection 0 -SkipHttpErrorCheck -ErrorAction SilentlyContinue | Out-Null
$opsCookie = $session.Cookies.GetAllCookies() | Where-Object Name -eq 'OPS_SESSION' | Select-Object -First 1
if (-not $opsCookie) { throw 'UI login gave no OPS_SESSION cookie.' }
$token = ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String([uri]::UnescapeDataString($opsCookie.Value))) |
    ConvertFrom-Json).csrfToken
if (-not $token) { throw 'No csrfToken in the OPS_SESSION cookie.' }
Write-Detail 'Logged in, session token received'

function Invoke-UiAction([string]$Page, [hashtable]$Fields) {
    $Fields.secureToken = $token
    $Fields.currentComponentInfo = 'TODO'
    $r = Invoke-WebRequest -Method Post "$ui/$Page" @web -Body $Fields -Headers @{ 'X-Requested-With' = 'XMLHttpRequest' }
    $r.Content ? ($r.Content | ConvertFrom-Json) : $null
}

# --- Upload ------------------------------------------------------------------
Write-Step 3 'Uploading the pak, signature checking ignored (usually 30-60 s, no progress shown by the server)'
Invoke-UiAction 'utility.action' @{ mainAction = 'prepareFileUpload' } | Out-Null
$uploadId = [DateTimeOffset]::Now.ToUnixTimeMilliseconds()
$r = Invoke-WebRequest -Method Post "$ui/admin/services/solution/upload?uploadId=$uploadId&ignoreSignatureChecking=true" @web `
    -Headers @{ secureToken = $token; Accept = 'application/json, text/javascript, */*; q=0.01' } `
    -Form @{ secureToken = $token; forceUpload = 'true'; forceContent = 'false'; solution = Get-Item $Pak; currentComponentInfo = 'TODO' }
$upload = $r.Content | ConvertFrom-Json
if (-not $upload.success -or -not $upload.pakId) { throw "Upload failed: $($r.Content)" }
Write-Detail "Uploaded as $($upload.pakId): $($upload.solutionName) $($upload.solutionVersion), $($upload.signingStatus)"

# --- Install -----------------------------------------------------------------
Write-Step 4 'Reading the EULA, as the UI does before an install'
Invoke-UiAction 'solution.action' @{ mainAction = 'getLicenseAgreement' } | Out-Null
Write-Detail 'Done'

Write-Step 5 'Starting the install'
Invoke-UiAction 'solution.action' @{ mainAction = 'install' } | Out-Null
Write-Detail 'Install started'

Write-Step 6 "Waiting for the install to finish (checked every 10 s, gives up after $TimeoutMinutes min)"
$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
do {
    Start-Sleep -Seconds 10
    $status = Get-Casa "upgrade/cluster/pak/$($upload.pakId)/status"
    $states = ($status.slices | ForEach-Object { "$($_.document.pak_state) on $($_.slice_address)" }) -join ', '
    Write-Detail "$($status.cluster_pak_install_status): $states"
} while ($status.cluster_pak_install_status -notin 'COMPLETED', 'FAILED', 'CANCELED' -and (Get-Date) -lt $deadline)

if ($status.cluster_pak_install_status -ne 'COMPLETED') {
    $details = $status.slices.document | ForEach-Object { $_.failed_details } | Where-Object { $_ }
    Write-Error "Install of $($upload.pakId) ended as $($status.cluster_pak_install_status). $($details | ConvertTo-Json -Compress -Depth 5)" -ErrorAction Continue
    exit 1
}
Write-Host ("Installed {0} on {1} in {2:m\:ss}" -f $upload.pakId, $hostName, $clock.Elapsed) -ForegroundColor Green
