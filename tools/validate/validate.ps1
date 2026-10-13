#Requires -Version 7
<#
.SYNOPSIS
  Read-only live check that the vCommunity adapter installed on a VCF Operations
  instance is collecting and that its data is landing on the vCenter objects.

.DESCRIPTION
  Talks to the Suite API only with GET calls (plus the token request). Nothing is
  changed on the instance. Exits 0 when no check fails, 1 otherwise.

  It tests the build that is INSTALLED on the instance, not the code in this repo.

.EXAMPLE
  pwsh tools/validate/validate.ps1
  Uses .secrets/vcf-ops.xml (see "Creating the secret file" below).

.EXAMPLE
  pwsh tools/validate/validate.ps1 -Url https://ops.example.com -Credential (Get-Credential) -SampleSize 0
  Checks every object instead of a sample.

.NOTES
  Creating the secret file (Windows, encrypted for the current user):
    [pscustomobject]@{ Url = 'https://<ops-host>/'; Credential = Get-Credential } |
        Export-Clixml .secrets/vcf-ops.xml
#>
[CmdletBinding()]
param(
    [string]$Url,
    [pscredential]$Credential,
    [string]$SecretFile = (Join-Path $PSScriptRoot '..\..\.secrets\vcf-ops.xml'),
    # Objects checked per object type. 0 = all.
    [int]$SampleSize = 5,
    # Newest vCommunity metric and last collection must be younger than this.
    [int]$MaxAgeMinutes = 20
)

$ErrorActionPreference = 'Stop'
$ADAPTER_KIND = 'vCommunity'
$PREFIX = 'vCommunity|*'

# What each vCenter object type is expected to carry. Datastore is properties-only
# by design; Datacenter only gets a metric when network speed data exists.
$EXPECTED = [ordered]@{
    'VirtualMachine'         = @{ Properties = $true;  Metrics = $true  }
    'HostSystem'             = @{ Properties = $true;  Metrics = $true  }
    'ClusterComputeResource' = @{ Properties = $true;  Metrics = $true  }
    'Datastore'              = @{ Properties = $true;  Metrics = $false }
    'VMwareAdapter Instance' = @{ Properties = $false; Metrics = $true  }
    'vSphere World'          = @{ Properties = $false; Metrics = $true  }
    'Datacenter'             = @{ Properties = $false; Metrics = $false }
}

$results = [System.Collections.Generic.List[object]]::new()
function Add-Result([string]$Status, [string]$Check, [string]$Detail) {
    $results.Add([pscustomobject]@{ Status = $Status; Check = $Check; Detail = $Detail })
}
function Get-AgeMinutes([long]$EpochMs) {
    [math]::Round(([DateTimeOffset]::Now - [DateTimeOffset]::FromUnixTimeMilliseconds($EpochMs)).TotalMinutes)
}

if ((-not $Url -or -not $Credential) -and (Test-Path $SecretFile)) {
    $secret = Import-Clixml $SecretFile
    if (-not $Url) { $Url = $secret.Url }
    if (-not $Credential) { $Credential = $secret.Credential }
}
if (-not $Url -or -not $Credential) {
    throw "No URL/credential. Pass -Url and -Credential, or create $SecretFile (see Get-Help $PSCommandPath -Full)."
}

$base = $Url.TrimEnd('/') + '/suite-api/api'
$headers = @{ Accept = 'application/json' }
$web = @{ SkipCertificateCheck = $true; TimeoutSec = 90 }
function Get-Api([string]$Path) { Invoke-RestMethod -Uri "$base/$Path" -Headers $headers @web }

try {
    # --- Login -------------------------------------------------------------
    $body = @{ username = $Credential.UserName; password = $Credential.GetNetworkCredential().Password } | ConvertTo-Json
    $token = Invoke-RestMethod -Method Post -Uri "$base/auth/token/acquire" -Body $body -ContentType 'application/json' -Headers $headers @web
    $headers.Authorization = "OpsToken $($token.token)"
    $version = Get-Api 'versions/current'
    Add-Result 'PASS' 'Login' "$($version.releaseName) build $($version.buildNumber) as $($Credential.UserName)"

    # --- Platform ----------------------------------------------------------
    $node = Get-Api 'deployment/node/status'
    Add-Result ($node.status -eq 'ONLINE' ? 'PASS' : 'FAIL') 'Node status' $node.status

    # --- Adapter kind and instances ------------------------------------------
    $kind = (Get-Api 'adapterkinds').'adapter-kind' | Where-Object key -eq $ADAPTER_KIND
    if ($kind) { Add-Result 'PASS' 'Adapter installed' "$($kind.name), $($kind.resourceKinds.Count) resource kinds" }
    else { Add-Result 'FAIL' 'Adapter installed' "Adapter kind '$ADAPTER_KIND' not found" }

    $instances = @((Get-Api "adapters?adapterKindKey=$ADAPTER_KIND").adapterInstancesInfoDto)
    if (-not $instances.Count) { Add-Result 'FAIL' 'Adapter instances' 'None configured' }
    foreach ($inst in $instances) {
        $name = "Instance '$($inst.resourceKey.name)'"
        $res = Get-Api "resources/$($inst.id)"
        $states = @($res.resourceStatusStates | ForEach-Object { "$($_.resourceState)/$($_.resourceStatus)" })
        $collecting = $states -contains 'STARTED/DATA_RECEIVING'
        Add-Result ($collecting ? 'PASS' : 'FAIL') "$name state" ("$($states -join ', '), health $($res.resourceHealth) $($inst.messageFromAdapterInstance)".Trim())
        if ($inst.lastCollected) {
            $age = Get-AgeMinutes $inst.lastCollected
            Add-Result ($age -le $MaxAgeMinutes ? 'PASS' : 'FAIL') "$name last collection" "$age min ago (limit $MaxAgeMinutes)"
        } else {
            Add-Result 'FAIL' "$name last collection" 'Never collected'
        }
    }

    # --- Data on vCenter objects ---------------------------------------------
    foreach ($type in $EXPECTED.Keys) {
        $want = $EXPECTED[$type]
        $all = @((Get-Api "resources?adapterKind=VMWARE&resourceKind=$([uri]::EscapeDataString($type))&pageSize=5000").resourceList)
        if (-not $all.Count) { Add-Result 'WARN' $type 'No objects of this type on the instance'; continue }
        $sample = $SampleSize -gt 0 ? @($all | Select-Object -First $SampleSize) : $all

        $withProps = 0; $withMetrics = 0; $newest = 0
        foreach ($obj in $sample) {
            $props = @((Get-Api "resources/$($obj.identifier)/properties").property | Where-Object name -like $PREFIX)
            if ($props.Count) { $withProps++ }
            $stats = @((Get-Api "resources/stats/latest?resourceId=$($obj.identifier)").values.'stat-list'.stat | Where-Object { $_.statKey.key -like $PREFIX })
            if ($stats.Count) {
                $withMetrics++
                $ts = ($stats | ForEach-Object { $_.timestamps } | Measure-Object -Maximum).Maximum
                if ($ts -gt $newest) { $newest = $ts }
            }
        }

        $n = $sample.Count
        $status = 'PASS'
        $notes = @()
        foreach ($what in 'Properties', 'Metrics') {
            if (-not $want[$what]) { continue }
            $have = $what -eq 'Properties' ? $withProps : $withMetrics
            if ($have -eq 0) { $status = 'FAIL'; $notes += "no $($what.ToLower())" }
            elseif ($have -lt $n) { if ($status -eq 'PASS') { $status = 'WARN' }; $notes += "$($n - $have) without $($what.ToLower())" }
        }
        $ageText = 'n/a'
        if ($newest) {
            $age = Get-AgeMinutes $newest
            $ageText = "$age min"
            if ($want.Metrics -and $age -gt $MaxAgeMinutes) { $status = 'FAIL'; $notes += "metrics stale" }
        }
        $detail = "$n of $($all.Count) checked: properties $withProps, metrics $withMetrics, newest metric $ageText"
        if ($notes) { $detail += " -- $($notes -join '; ')" }
        Add-Result $status $type $detail
    }
} catch {
    $msg = $_.Exception.Message
    if ($_.ErrorDetails.Message) { $msg += " | $($_.ErrorDetails.Message)" }
    Add-Result 'FAIL' 'Script error' $msg
}

$results | Format-Table -AutoSize -Wrap | Out-String -Width 200 | Write-Host
$fail = @($results | Where-Object Status -eq 'FAIL').Count
$warn = @($results | Where-Object Status -eq 'WARN').Count
Write-Host "RESULT: $($fail ? 'FAILED' : 'PASSED')  ($($results.Count - $fail - $warn) pass, $warn warn, $fail fail)"
exit ($fail ? 1 : 0)
