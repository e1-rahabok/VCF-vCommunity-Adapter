#Requires -Version 7
<#
.SYNOPSIS
  Stop and start collection on every Adapter Instance of the vCommunity pack, and
  wait until each one is collecting again.

.DESCRIPTION
  After a pak upgrade, the pack's Adapter Instances often stop collecting until
  collection is restarted (docs/installation-guide/installation.md, "After an
  Upgrade: Restart Collection"). This does the same as Stop Collecting and Start
  Collecting in Administration > Integrations > Accounts, for every instance of
  adapter kind vCommunity, through the Suite API:

    PUT /suite-api/api/adapters/{adapterId}/monitoringstate/stop
    PUT /suite-api/api/adapters/{adapterId}/monitoringstate/start

  This CHANGES the instance: collection of this pack stops for a moment. No other
  adapter is touched. Exits 0 only when every instance reports
  STARTED/DATA_RECEIVING, 1 otherwise.

.EXAMPLE
  pwsh tools/restart/restart.ps1
  Uses .secrets/vcf-ops.xml (see tools/validate/validate.md, "Requirements").

.EXAMPLE
  pwsh tools/restart/restart.ps1 -Url https://ops.example.com -Credential (Get-Credential)
#>
[CmdletBinding()]
param(
    [string]$Url,
    [pscredential]$Credential,
    [string]$SecretFile = (Join-Path $PSScriptRoot '..\..\.secrets\vcf-ops.xml'),
    # How long to wait for every instance to collect again after the start.
    [int]$TimeoutMinutes = 15,
    # How long to wait for every instance to report stopped before starting it.
    [int]$StopTimeoutMinutes = 2
)

$ErrorActionPreference = 'Stop'
$ADAPTER_KIND = 'vCommunity'
$COLLECTING = 'STARTED/DATA_RECEIVING'
$POLL_SECONDS = 15

if ((-not $Url -or -not $Credential) -and (Test-Path $SecretFile)) {
    $secret = Import-Clixml $SecretFile
    if (-not $Url) { $Url = $secret.Url }
    if (-not $Credential) { $Credential = $secret.Credential }
}
if (-not $Url -or -not $Credential) {
    throw "No URL/credential. Pass -Url and -Credential, or create $SecretFile (see tools/validate/validate.md)."
}

$base = $Url.TrimEnd('/') + '/suite-api/api'
$headers = @{ Accept = 'application/json' }
$web = @{ SkipCertificateCheck = $true; TimeoutSec = 90 }
function Get-Api([string]$Path) { Invoke-RestMethod -Uri "$base/$Path" -Headers $headers @web }
function Invoke-PutApi([string]$Path) { Invoke-RestMethod -Method Put -Uri "$base/$Path" -Headers $headers @web | Out-Null }

$clock = [Diagnostics.Stopwatch]::StartNew()
function Write-Step([int]$Number, [string]$Text) {
    Write-Host ("[{0}/5] {1}" -f $Number, $Text) -ForegroundColor Cyan
}
function Write-Detail([string]$Text) {
    Write-Host ("      {0}  ({1:m\:ss})" -f $Text, $clock.Elapsed)
}
# State of one Adapter Instance, as Administration > Integrations > Accounts shows it: STATE/STATUS.
function Get-State([string]$Id) {
    $res = Get-Api "resources/$Id"
    @($res.resourceStatusStates | ForEach-Object { "$($_.resourceState)/$($_.resourceStatus)" }) -join ', '
}
# Polls every instance until Test returns true for all of them, or the deadline passes.
# Prints an instance's state each time it changes. Returns the last state of each.
function Wait-State([object[]]$Instances, [scriptblock]$Test, [int]$Minutes) {
    $deadline = (Get-Date).AddMinutes($Minutes)
    $last = @{}
    while ($true) {
        foreach ($i in $Instances) {
            $state = Get-State $i.id
            if ($last[$i.id] -ne $state) { Write-Detail "'$($i.resourceKey.name)': $state"; $last[$i.id] = $state }
        }
        if (-not @($Instances | Where-Object { -not (& $Test $last[$_.id]) }).Count) { return $last }
        if ((Get-Date) -ge $deadline) { return $last }
        Start-Sleep -Seconds $POLL_SECONDS
    }
}

try {
    # --- Login -----------------------------------------------------------------
    Write-Step 1 "Logging in to $(([uri]$Url).Host) as $($Credential.UserName)"
    $body = @{ username = $Credential.UserName; password = $Credential.GetNetworkCredential().Password } | ConvertTo-Json
    $token = Invoke-RestMethod -Method Post -Uri "$base/auth/token/acquire" -Body $body -ContentType 'application/json' -Headers $headers @web
    $headers.Authorization = "OpsToken $($token.token)"
    $version = Get-Api 'versions/current'
    Write-Detail "$($version.releaseName) build $($version.buildNumber)"

    # --- Adapter Instances -----------------------------------------------------------
    Write-Step 2 "Finding the Adapter Instances of adapter kind $ADAPTER_KIND"
    $instances = @((Get-Api "adapters?adapterKindKey=$ADAPTER_KIND").adapterInstancesInfoDto | Where-Object { $_ })
    if (-not $instances.Count) { throw "No Adapter Instance of adapter kind '$ADAPTER_KIND' found." }
    foreach ($i in $instances) { Write-Detail "'$($i.resourceKey.name)' ($($i.id)): $(Get-State $i.id)" }

    # --- Stop --------------------------------------------------------------------------
    Write-Step 3 "Stopping collection on $($instances.Count) instance(s)"
    foreach ($i in $instances) {
        Invoke-PutApi "adapters/$($i.id)/monitoringstate/stop"
        Write-Detail "'$($i.resourceKey.name)': stop requested"
    }
    # Wait for STOPPED itself: a start sent while an instance is still STOPPING is
    # ignored, and the instance then stays STOPPED.
    $stopped = Wait-State $instances { param($s) $s -match '^STOPPED' } $StopTimeoutMinutes
    foreach ($i in $instances | Where-Object { $stopped[$_.id] -notmatch '^STOPPED' }) {
        Write-Detail "'$($i.resourceKey.name)': still $($stopped[$i.id]) after $StopTimeoutMinutes min, starting it anyway"
    }

    # --- Start -------------------------------------------------------------------------
    Write-Step 4 "Starting collection on $($instances.Count) instance(s)"
    foreach ($i in $instances) {
        Invoke-PutApi "adapters/$($i.id)/monitoringstate/start"
        Write-Detail "'$($i.resourceKey.name)': start requested"
    }

    # --- Wait --------------------------------------------------------------------------
    Write-Step 5 "Waiting until every instance is $COLLECTING (checked every $POLL_SECONDS s, gives up after $TimeoutMinutes min)"
    $final = Wait-State $instances { param($s) $s -eq $COLLECTING } $TimeoutMinutes
} catch {
    $msg = "$($_.Exception.Message) (line $($_.InvocationInfo.ScriptLineNumber))"
    if ($_.ErrorDetails.Message) { $msg += " | $($_.ErrorDetails.Message)" }
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

$notCollecting = @($instances | Where-Object { $final[$_.id] -ne $COLLECTING })
foreach ($i in $instances) {
    $ok = $final[$i.id] -eq $COLLECTING
    Write-Host ("{0}  '{1}': {2}" -f ($ok ? 'PASS' : 'FAIL'), $i.resourceKey.name, $final[$i.id]) -ForegroundColor ($ok ? 'Green' : 'Red')
}
if ($notCollecting.Count) {
    Write-Host ("RESULT: FAILED  {0} of {1} instance(s) not collecting after {2:m\:ss}" -f $notCollecting.Count, $instances.Count, $clock.Elapsed) -ForegroundColor Red
    exit 1
}
Write-Host ("RESULT: PASSED  {0} instance(s) collecting after {1:m\:ss}" -f $instances.Count, $clock.Elapsed) -ForegroundColor Green
exit 0
