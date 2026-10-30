#Requires -Version 7
<#
.SYNOPSIS
  Read-only live check that the vCommunity adapter installed on a VCF Operations
  instance is collecting and that its data is landing on the vCenter objects.

.DESCRIPTION
  Talks to the Suite API only with GET calls (plus the token request). Nothing is
  changed on the instance. Exits 0 when no check fails, 1 otherwise.
  The one exception is -Release: it starts a content export job (a POST) to check
  the pack's views and dashboards. The export changes no content.

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
    [int]$MaxAgeMinutes = 20,
    # Version the installed pack must have. A mismatch FAILs. When omitted, the
    # version in manifest.txt is compared and a mismatch only WARNs.
    [string]$ExpectedVersion,
    # Release sign-off: also export the content and check the pack's views and
    # dashboards. This starts a content export job on the instance (a POST).
    [switch]$Release,
    # A gap between two samples longer than this is reported by the continuity check.
    [int]$MaxGapMinutes = 15
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

    $strict = [bool]$ExpectedVersion
    if (-not $strict) {
        $ExpectedVersion = (Get-Content (Join-Path $PSScriptRoot '..\..\Management Pack\manifest.txt') -Raw | ConvertFrom-Json).version
    }
    $solution = (Get-Api 'solutions').solution | Where-Object { $_.adapterKindKeys -contains $ADAPTER_KIND } | Select-Object -First 1
    if (-not $solution) { Add-Result 'FAIL' 'Installed version' "No solution for adapter kind '$ADAPTER_KIND'" }
    elseif ($solution.version -eq $ExpectedVersion -or $solution.version -like "$ExpectedVersion.*") {
        Add-Result 'PASS' 'Installed version' "$($solution.version) (expected $ExpectedVersion)"
    } else {
        $source = $strict ? '-ExpectedVersion' : 'manifest.txt'
        Add-Result ($strict ? 'FAIL' : 'WARN') 'Installed version' "$($solution.version), but $source says $ExpectedVersion"
    }

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

    # --- Business Application performance on the Container objects -----------
    # WARN, not FAIL, when no object has a value: a Tier whose VMs are all powered off has none, by design.
    $BUSINESS = [ordered]@{
        'Tier'            = 'vCommunity|Business Application|Tier Performance'
        'BusinessService' = 'vCommunity|Business Application|Business Application Performance'
        'Enterprise'      = 'vCommunity|Business Application|Business Applications Performance'
    }
    foreach ($kind in $BUSINESS.Keys) {
        $key = $BUSINESS[$kind]
        $objects = @((Get-Api "resources?adapterKind=Container&resourceKind=$kind&pageSize=5000").resourceList)
        if (-not $objects.Count) { Add-Result 'WARN' "Business Application $kind" 'No objects of this kind on the instance'; continue }
        $withValue = 0
        foreach ($obj in $objects) {
            $stat = @((Get-Api "resources/stats/latest?resourceId=$($obj.identifier)").values.'stat-list'.stat | Where-Object { $_.statKey.key -eq $key })
            if ($stat.Count -and @($stat[0].data).Count) { $withValue++ }
        }
        $status = $withValue ? 'PASS' : 'WARN'
        Add-Result $status "Business Application $kind" "$withValue of $($objects.Count) have $key"
    }

    # --- Cluster KPIs and the Periodic Cluster Check -------------------------
    $KPI = [ordered]@{
        Performance = 'vCommunity|Cluster Performance|Cluster Performance Score'
        Risk        = 'vCommunity|Cluster Risk|Cluster Risk Score'
        Consumption = 'vCommunity|Cluster Consumption|Cluster Consumption Score'
    }
    $CHECK = 'vCommunity|Periodic Cluster Check|'
    $CHECK_KEYS = 'Worst Cluster Performance', 'Worst Cluster Risk', 'Worst Cluster Consumption', 'Close for Business' |
        ForEach-Object { "$CHECK$_" }
    $clusters = @((Get-Api "resources?adapterKind=VMWARE&resourceKind=ClusterComputeResource&pageSize=5000").resourceList)
    $clusterSample = $SampleSize -gt 0 ? @($clusters | Select-Object -First $SampleSize) : $clusters

    # Latest value and time of every vCommunity stat of one object: @{ key = @{ Value; Time (epoch ms) } }.
    function Get-Latest([string]$ResourceId) {
        $latest = @{}
        foreach ($s in @((Get-Api "resources/stats/latest?resourceId=$ResourceId").values.'stat-list'.stat | Where-Object { $_ })) {
            if ($s.statKey.key -like $PREFIX) {
                $latest[$s.statKey.key] = @{ Value = @($s.data)[-1]; Time = [long]@($s.timestamps)[-1] }
            }
        }
        $latest
    }
    # 5-minute samples of some stats of one object between two times: @{ key = @(epoch ms, ...) }.
    function Get-SampleTimes([string]$ResourceId, [string[]]$Keys, [long]$Begin, [long]$End) {
        $query = ($Keys | ForEach-Object { "statKey=$([uri]::EscapeDataString($_))" }) -join '&'
        $r = Get-Api "resources/$ResourceId/stats?$query&begin=$Begin&end=$End&rollUpType=AVG&intervalType=MINUTES&intervalQuantifier=5"
        $times = @{}
        foreach ($s in @($r.values.'stat-list'.stat | Where-Object { $_.statKey.key })) {
            $times[$s.statKey.key] = @($s.timestamps | ForEach-Object { [long]$_ })
        }
        $times
    }
    # The KPI band of a value, on its health (the value, or 100 minus it when higher is worse).
    # The same limits as band() in metrics/cluster/periodic_cluster_check.py.
    function Get-Band([double]$Value, [bool]$HigherIsWorse) {
        $health = $HigherIsWorse ? 100 - $Value : $Value
        if ($health -lt 25) { 'red' } elseif ($health -lt 50) { 'orange' } elseif ($health -lt 75) { 'yellow' } else { 'green' }
    }

    if (-not $clusterSample.Count) {
        Add-Result 'WARN' 'Cluster KPIs' 'No clusters on the instance'
    } else {
        $latestByCluster = @{}
        foreach ($cl in $clusterSample) { $latestByCluster[$cl.identifier] = Get-Latest $cl.identifier }
        $nowMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()

        # Every cluster has a current value of each KPI.
        $status = 'PASS'; $parts = @()
        foreach ($name in $KPI.Keys) {
            $fresh = @($clusterSample | Where-Object {
                $v = $latestByCluster[$_.identifier][$KPI[$name]]
                $v -and ($nowMs - $v.Time) / 60000 -le $MaxAgeMinutes }).Count
            $parts += "$name $fresh/$($clusterSample.Count)"
            if ($fresh -eq 0) { $status = 'FAIL' } elseif ($fresh -lt $clusterSample.Count -and $status -eq 'PASS') { $status = 'WARN' }
        }
        Add-Result $status 'Cluster KPIs' "current (within $MaxAgeMinutes min): $($parts -join ', ')"

        # No collection gap in the last 24 hours, on the Cluster Risk Score of the first cluster.
        $first = $clusterSample[0]
        $times = (Get-SampleTimes $first.identifier @($KPI.Risk) ($nowMs - 24 * 3600000) $nowMs)[$KPI.Risk]
        if (-not $times) {
            Add-Result 'WARN' 'Collection continuity' "No Cluster Risk Score in the last 24 hours on $($first.resourceKey.name)"
        } else {
            $gaps = @(for ($i = 1; $i -lt $times.Count; $i++) {
                $minutes = ($times[$i] - $times[$i - 1]) / 60000
                if ($minutes -gt $MaxGapMinutes) {
                    [pscustomobject]@{ From = $times[$i - 1]; To = $times[$i]; Minutes = [math]::Round($minutes) }
                }
            })
            if ($gaps) {
                $largest = $gaps | Sort-Object Minutes -Descending | Select-Object -First 1
                $when = '{0:MM-dd HH:mm} to {1:MM-dd HH:mm} UTC' -f [DateTimeOffset]::FromUnixTimeMilliseconds($largest.From).UtcDateTime,
                    [DateTimeOffset]::FromUnixTimeMilliseconds($largest.To).UtcDateTime
                Add-Result 'WARN' 'Collection continuity' "$($gaps.Count) gap(s) over $MaxGapMinutes min in 24 h; largest $($largest.Minutes) min, $when"
            } else {
                Add-Result 'PASS' 'Collection continuity' "$($times.Count) samples in 24 h, no gap over $MaxGapMinutes min"
            }
        }

        # The Periodic Cluster Check published for the latest window that ended, allowing 3 cycles for it to run.
        $ids = @($instances | ForEach-Object { $_.resourceKey.resourceIdentifiers }) | Group-Object { $_.identifierType.name } -AsHashTable -AsString
        $periodText = $ids -and $ids['cluster_check_period_hours'] ? "$($ids['cluster_check_period_hours'][0].value)" : ''
        $timeText = $ids -and $ids['periodic_cluster_check_time'] ? "$($ids['periodic_cluster_check_time'][0].value)" : ''
        $period = $periodText -match '^\d+$' -and [int]$periodText -in 1, 2, 4, 6, 8, 12, 24 ? [int]$periodText : 24
        $hour, $minute = 0, 0
        if ($timeText -match '^\s*(\d{1,2}):(\d{2})\s*$' -and [int]$Matches[1] -le 23 -and [int]$Matches[2] -le 59) { $hour, $minute = [int]$Matches[1], [int]$Matches[2] }
        $reference = [DateTimeOffset]::UtcNow.AddMinutes(-15)
        $anchor = [DateTimeOffset]::new($reference.Year, $reference.Month, $reference.Day, $hour, $minute, 0, [TimeSpan]::Zero).AddDays(-1)
        $windowEnd = $anchor.AddHours($period * [math]::Floor(($reference - $anchor).TotalHours / $period))
        $endMs = $windowEnd.ToUnixTimeMilliseconds(); $beginMs = $windowEnd.AddHours(-$period).ToUnixTimeMilliseconds()
        $onTime = 0; $noData = @(); $late = @()
        foreach ($cl in $clusterSample) {
            $latest = $latestByCluster[$cl.identifier]
            $calculated = ($CHECK_KEYS | ForEach-Object { $latest[$_] ? $latest[$_].Time : 0 } | Measure-Object -Maximum).Maximum
            if ($calculated -ge $endMs) { $onTime++; continue }
            $inWindow = (Get-SampleTimes $cl.identifier @($KPI.Values) $beginMs $endMs).Values | ForEach-Object { $_ } | Where-Object { $_ -ge $beginMs -and $_ -lt $endMs }
            if ($inWindow) { $late += $cl.resourceKey.name } else { $noData += $cl.resourceKey.name }
        }
        $window = "window to {0:yyyy-MM-dd HH:mm} UTC ({1} h)" -f $windowEnd.UtcDateTime, $period
        if ($late) { Add-Result 'FAIL' 'Periodic Cluster Check' "$window not calculated, with KPI data, on: $($late -join ', ')" }
        elseif ($noData) { Add-Result 'WARN' 'Periodic Cluster Check' "$window has no KPI data, so nothing to calculate, on: $($noData -join ', ') (collection gap?)" }
        else { Add-Result 'PASS' 'Periodic Cluster Check' "$window calculated on $onTime/$($clusterSample.Count)" }

        # Close for Business follows the rule from the published Worst values.
        $checked = 0; $wrong = @()
        foreach ($cl in $clusterSample) {
            $latest = $latestByCluster[$cl.identifier]
            if (@($CHECK_KEYS | Where-Object { -not $latest[$_] }).Count) { continue }
            $times = $CHECK_KEYS | ForEach-Object { $latest[$_].Time }
            if ((($times | Measure-Object -Maximum).Maximum - ($times | Measure-Object -Minimum).Minimum) -gt 60000) { continue }
            $performance = Get-Band $latest["${CHECK}Worst Cluster Performance"].Value $false
            $risk = Get-Band $latest["${CHECK}Worst Cluster Risk"].Value $true
            $consumption = Get-Band $latest["${CHECK}Worst Cluster Consumption"].Value $true
            $expected = ($performance -eq 'red' -or $consumption -eq 'red') -or
                        ($performance -eq 'orange' -and $consumption -eq 'orange' -and $risk -in 'orange', 'red') ? 1 : 0
            $actual = [int]$latest["${CHECK}Close for Business"].Value
            $checked++
            if ($actual -ne $expected) { $wrong += "$($cl.resourceKey.name): published $actual, rule gives $expected (Performance $performance, Risk $risk, Consumption $consumption)" }
        }
        if ($wrong) { Add-Result 'FAIL' 'Close for Business rule' ($wrong -join '; ') }
        elseif (-not $checked) { Add-Result 'WARN' 'Close for Business rule' 'No cluster has a complete result yet (all four check metrics from one calculation)' }
        else { Add-Result 'PASS' 'Close for Business rule' "matches the rule on $checked/$($clusterSample.Count)" }
    }

    # --- Content (release sign-off only) -------------------------------------
    if ($Release) {
        Add-Type -AssemblyName System.IO.Compression
        $deadline = (Get-Date).AddMinutes(10)
        # An export another run started may still be going: a new one is refused until it finishes.
        $previous = Get-Api 'content/operations/export'
        while ($previous.state -in 'RUNNING', 'NOT_INITIALIZED' -and (Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 5; $previous = Get-Api 'content/operations/export'
        }
        $request = @{ scope = 'ALL'; contentTypes = @('VIEW_DEFINITIONS', 'DASHBOARDS') } | ConvertTo-Json
        Invoke-RestMethod -Method Post -Uri "$base/content/operations/export" -Body $request -ContentType 'application/json' -Headers $headers @web | Out-Null
        # The status describes the last export until this run's job replaces it, and the last one may already be
        # FINISHED. So wait for a job with a different id, and then for that job to finish. Each job has its own id.
        do { Start-Sleep -Seconds 5; $export = Get-Api 'content/operations/export' } while (
            ($export.id -eq $previous.id -or $export.state -in 'RUNNING', 'NOT_INITIALIZED') -and (Get-Date) -lt $deadline)
        if ($export.id -eq $previous.id) {
            Add-Result 'FAIL' 'Content export' 'The export did not start within 10 minutes'
        } elseif ($export.state -ne 'FINISHED') {
            Add-Result 'FAIL' 'Content export' "Export ended as $($export.state) $($export.errorMessages -join ' ')"
        } else {
            $zipFile = [IO.Path]::GetTempFileName()
            try {
                $zipHeaders = $headers.Clone(); $zipHeaders.Accept = 'application/octet-stream'
                # FINISHED can be reported a little before the zip can be downloaded: "No data available for the last
                # export operation". Retry for up to 3 minutes, and fail with that message if it never becomes available.
                $zipDeadline = (Get-Date).AddMinutes(3)
                while ($true) {
                    try {
                        Invoke-WebRequest -Uri "$base/content/operations/export/zip" -Headers $zipHeaders -OutFile $zipFile @web
                        break
                    } catch {
                        if ((Get-Date) -ge $zipDeadline) { throw }
                        Start-Sleep -Seconds 10
                    }
                }
                $outer = [IO.Compression.ZipFile]::OpenRead($zipFile)
                function Read-Entry($Archive, [string]$Name) {
                    $stream = $Archive.GetEntry($Name).Open(); $memory = [IO.MemoryStream]::new(); $stream.CopyTo($memory); $stream.Dispose(); $memory
                }
                function Read-Text($Archive, [string]$Name) { [Text.Encoding]::UTF8.GetString((Read-Entry $Archive $Name).ToArray()).TrimStart([char]0xFEFF) }

                $viewsZip = [IO.Compression.ZipArchive]::new((Read-Entry $outer 'views.zip'))
                $viewRegex = '<ViewDef id="([^"]+)">.*?</ViewDef>'
                # VCF Operations renumbers the internal control IDs (such as pagination-control_id_109) on import,
                # so they are left out of the comparison, like whitespace.
                function Get-Normalised([string]$Block) { ($Block -replace '_id_\d+', '_id_N') -replace '\s+', ' ' }
                $exported = @{}; $duplicates = 0
                foreach ($m in [regex]::Matches((Read-Text $viewsZip 'content.xml'), $viewRegex, 'Singleline')) {
                    if ($exported.ContainsKey($m.Groups[1].Value)) { $duplicates++ }
                    $exported[$m.Groups[1].Value] = Get-Normalised $m.Value
                }
                # A view can be shipped in more than one file. It matches when the instance has any of its copies.
                $shippedViews = @{}
                foreach ($file in Get-ChildItem (Join-Path $PSScriptRoot '..\..\Management Pack\content\reports') -Filter *.xml) {
                    foreach ($m in [regex]::Matches((Get-Content $file -Raw), $viewRegex, 'Singleline')) {
                        if (-not $shippedViews.ContainsKey($m.Groups[1].Value)) { $shippedViews[$m.Groups[1].Value] = @() }
                        $shippedViews[$m.Groups[1].Value] += [pscustomobject]@{ File = $file.BaseName; Block = Get-Normalised $m.Value }
                    }
                }
                $missing = @(); $changed = @(); $conflicting = @()
                foreach ($id in $shippedViews.Keys) {
                    $copies = $shippedViews[$id]
                    if (@($copies.Block | Select-Object -Unique).Count -gt 1) { $conflicting += "$id in $(@($copies.File) -join ' and ')" }
                    if (-not $exported.ContainsKey($id)) { $missing += $copies[0].File }
                    elseif ($copies.Block -notcontains $exported[$id]) { $changed += $copies[0].File }
                }
                $status = $duplicates -or $missing ? 'FAIL' : ($changed ? 'WARN' : 'PASS')
                $detail = "$($shippedViews.Count) shipped, $($exported.Count) on the instance, duplicate IDs $duplicates, missing $($missing.Count), changed since install $($changed.Count)"
                if ($missing -or $changed) { $detail += " -- $(@($missing + $changed | Select-Object -Unique -First 5) -join ', ')" }
                Add-Result $status 'Content: views' $detail
                if ($conflicting) {
                    Add-Result 'WARN' 'Content: views shipped twice' "$($conflicting.Count) view(s) in two files with different content; the last imported wins -- $(@($conflicting | Select-Object -First 3) -join '; ')"
                }

                $dashboardCount = @{}
                foreach ($entry in $outer.Entries | Where-Object { $_.FullName -like 'dashboards/*' -and $_.Name }) {
                    $inner = [IO.Compression.ZipArchive]::new((Read-Entry $outer $entry.FullName))
                    foreach ($d in (Read-Text $inner 'dashboard/dashboard.json' | ConvertFrom-Json -Depth 100).dashboards) { $dashboardCount[$d.id] = 1 + [int]$dashboardCount[$d.id] }
                }
                $missing = @(); $doubled = @(); $shipped = 0
                foreach ($file in Get-ChildItem (Join-Path $PSScriptRoot '..\..\Management Pack\content\dashboards') -Filter *.json -Recurse) {
                    foreach ($d in (Get-Content $file -Raw | ConvertFrom-Json -Depth 100).dashboards) {
                        $shipped++
                        if (-not $dashboardCount[$d.id]) { $missing += $d.name } elseif ($dashboardCount[$d.id] -gt 1) { $doubled += $d.name }
                    }
                }
                $status = $missing -or $doubled ? 'FAIL' : 'PASS'
                $detail = "$shipped shipped, missing $($missing.Count), more than once $($doubled.Count)"
                if ($missing -or $doubled) { $detail += " -- $(@($missing + $doubled | Select-Object -First 5) -join ', ')" }
                Add-Result $status 'Content: dashboards' $detail
                $outer.Dispose()
            } finally {
                Remove-Item $zipFile -ErrorAction SilentlyContinue
            }
        }
    }
} catch {
    $msg = "$($_.Exception.Message) (line $($_.InvocationInfo.ScriptLineNumber))"
    if ($_.ErrorDetails.Message) { $msg += " | $($_.ErrorDetails.Message)" }
    Add-Result 'FAIL' 'Script error' $msg
}

$results | Format-Table -AutoSize -Wrap | Out-String -Width 200 | Write-Host
$fail = @($results | Where-Object Status -eq 'FAIL').Count
$warn = @($results | Where-Object Status -eq 'WARN').Count
Write-Host "RESULT: $($fail ? 'FAILED' : 'PASSED')  ($($results.Count - $fail - $warn) pass, $warn warn, $fail fail)"
exit ($fail ? 1 : 0)
