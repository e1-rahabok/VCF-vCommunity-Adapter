# Live Validation Test Plan

`validate.ps1` checks that the pack **installed on a VCF Operations instance** is collecting, and that its data lands on the vCenter objects under the `vCommunity|` prefix.

It is the second of two test layers. Run both after any change under `Management Pack/app`:

| Layer | Command | Tests |
| :--- | :--- | :--- |
| Unit tests | `python -m pytest tests`, from `Management Pack` | The code in this repo, with fakes. No live system. |
| Live validation | `pwsh tools/validate/validate.ps1` | The build installed on the instance. |

A code change is only covered by live validation once a pak built from it is installed on the instance.

## Safety

The script is read-only. It calls the Suite API with `GET` only, plus the login token request. It changes nothing on the instance.

## Requirements

- PowerShell 7 (`pwsh`).
- A VCF Operations account that can read adapters, solutions and resources.
- The URL and login, either as parameters or in `.secrets/vcf-ops.xml`. That file is gitignored: never commit it. Create it once, on the machine that runs the tests. It is encrypted for the Windows user who creates it:

  ```powershell
  New-Item -ItemType Directory -Force .secrets | Out-Null
  [pscustomobject]@{ Url = 'https://<ops-host>/'; Credential = Get-Credential } |
      Export-Clixml .secrets/vcf-ops.xml
  ```

## Running it

```powershell
# Day to day: the installed version is compared with manifest.txt, a mismatch only warns
pwsh tools/validate/validate.ps1

# Release sign-off: the installed version must match
pwsh tools/validate/validate.ps1 -ExpectedVersion 0.2.0

# Every object instead of a sample of 5 per type
pwsh tools/validate/validate.ps1 -SampleSize 0
```

| Parameter | Default | Meaning |
| :--- | :--- | :--- |
| `-ExpectedVersion` | version in `manifest.txt` | Version the installed pack must have. Passing it turns a mismatch from WARN into FAIL. |
| `-SampleSize` | `5` | Objects checked per object type. `0` checks all. |
| `-MaxAgeMinutes` | `20` | How old the last collection and the newest metric may be. |
| `-Url`, `-Credential`, `-SecretFile` | `.secrets/vcf-ops.xml` | Where to connect. |

Exit code `0` means no check failed. `1` means at least one FAIL. WARN lines do not fail the run, but report them.

## Test cases

### Platform and adapter

| # | Check | PASS when | Otherwise |
| :--- | :--- | :--- | :--- |
| 1 | Login | A token is issued. Shows release and build. | FAIL, and the run stops |
| 2 | Node status | The node reports `ONLINE` | FAIL |
| 3 | Adapter installed | Adapter kind `vCommunity` exists | FAIL |
| 4 | Installed version | The installed solution's version matches the expected version | WARN against `manifest.txt`, FAIL against `-ExpectedVersion` |
| 5 | Instance state | Each Adapter Instance is `STARTED/DATA_RECEIVING` | FAIL. No instances at all is also a FAIL. |
| 6 | Instance last collection | Each instance collected within `-MaxAgeMinutes` | FAIL, also when it never collected |

### Data on vCenter objects

For each object type, the script takes a sample of objects from the vCenter adapter and looks for `vCommunity|` properties and metrics on them.

| # | Object type | Properties expected | Metrics expected |
| :--- | :--- | :---: | :---: |
| 7 | VirtualMachine | Yes | Yes |
| 8 | HostSystem | Yes | Yes |
| 9 | ClusterComputeResource | Yes | Yes |
| 10 | Datastore | Yes | No, properties only by design |
| 11 | VMwareAdapter Instance | No | Yes |
| 12 | vSphere World | No | Yes |
| 13 | Datacenter | No | No, a metric appears only when network speed data exists |

Result for each type:

- **PASS**: every sampled object has what is expected, and the newest metric is within `-MaxAgeMinutes`.
- **WARN**: some sampled objects lack what is expected, or the instance has no objects of that type.
- **FAIL**: no sampled object has what is expected, or the expected metrics are stale.

## Release sign-off

Before publishing a release:

1. Unit tests pass.
2. The release pak is installed on the test instance, and at least one collection has run since.
3. `pwsh tools/validate/validate.ps1 -ExpectedVersion <version>` exits `0`.
4. Any WARN lines are explained in the release notes or fixed.

If an Adapter Instance is `FAILED` and has never collected right after the install, stop and start collecting on it (Integrations → Accounts), wait one collection cycle, and run the script again.

## Not covered

These need a manual check, or are not tested yet:

- Whether values are correct, for example a setting's value matching vCenter. The script checks that data exists and is fresh, not what it says.
- Dashboards, views, reports and super metrics in `content/`: whether they import and render.
- Upgrade from the previous version, and uninstall.
- Optional features that are off on the test instance, such as Windows Services and Event Logs through GuestAPI.
- Scale and collection duration.
