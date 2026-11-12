# Install Script

`install.ps1` uploads a built pak to a VCF Operations instance and installs it, with no browser and no file dialog. It is a development tool: it puts a new build on the test instance, so that the [live validation](../validate/validate.md) covers it.

Administrators install the pack through the UI: see [Installation](../../docs/installation-guide/installation.md).

## Safety

The script **changes the instance**. It replaces the installed version of the pack, the same as installing it from the UI.

It installs an **unsigned** pak, with signature checking ignored, the same as ticking **Ignore the PAK file signature checking** in the UI. Use it only with paks you built yourself from this repo.

It does not check the instance's TLS certificate (`-SkipCertificateCheck`), like `validate.ps1`. Use it only with a test instance on a trusted network.

## Requirements

- PowerShell 7 (`pwsh`).
- The local **`admin`** account. Steps 1 and 6 use the admin API, which accepts only that account.
- **Allow Unsigned PAK Installation** turned on, under `/admin` > **Administrator Settings** > **Security Settings**. It is off on a fresh 9.x install.
- The URL and login in `.secrets/vcf-ops.xml`, created as described in [Live Validation Test Plan](../validate/validate.md#requirements), or passed as parameters.
- A built pak. `pwsh tools/build/build.ps1` makes one in `Management Pack/build`: see [Build Script](../build/build.md).

## Running it

From the repo root:

```powershell
# The pak in "Management Pack/build" for the version in manifest.txt
pwsh tools/install/install.ps1

# A specific pak
pwsh tools/install/install.ps1 -Pak "Management Pack/build/vCommunity_<version>.pak"
```

| Parameter | Default | Meaning |
| :--- | :--- | :--- |
| `-Pak` | newest pak for the `manifest.txt` version | The pak to install. |
| `-TimeoutMinutes` | `20` | How long step 6 waits before giving up. |
| `-Url`, `-Credential`, `-SecretFile` | `.secrets/vcf-ops.xml` | Where to connect. |

Exit code `0` means the install completed, and `1` that it failed or timed out. An error stops the script, and the last `[n/6]` line shows which step failed.

## What it does

The script prints each step before it runs it, and the elapsed time after. The times below are from installing a 424 KB pak on a one-node VCF Operations 9.1.1 instance, 4 minutes 38 seconds in all.

| Step | What the script prints | Request | Time |
| :--- | :--- | :--- | :--- |
| 1 | Checking the instance is online and no other pak install is running | Admin API: `GET /casa/deployment/cluster/info` | under 1 s |
| 2 | Logging in to the VCF Operations UI | UI: `/ui/login.action`, then `/ui/index.action` for the session token | 2 s |
| 3 | Uploading the pak, signature checking ignored | UI: `/ui/utility.action` (`prepareFileUpload`), then `/ui/admin/services/solution/upload` | 42 s |
| 4 | Reading the EULA, as the UI does before an install | UI: `/ui/solution.action` (`getLicenseAgreement`) | under 1 s |
| 5 | Starting the install | UI: `/ui/solution.action` (`install`) | 3 s |
| 6 | Waiting for the install to finish | Admin API: `GET /casa/upgrade/cluster/pak/<pakId>/status`, every 10 s | 3 min 51 s |

### 1. Preflight

The script reads the cluster state from the admin API. It stops when the cluster is not `ONLINE`, or when `is_pak_installation_active` shows that another pak install is running. Only one install can run at a time.

### 2. Log in to the UI

The script logs in with a local account (`authSourceId=localItem`) and checks that the server answers `ok`.

Every later UI request must carry a CSRF token (`secureToken`). The token is in the `OPS_SESSION` cookie that `index.action` sets, as the `csrfToken` field of base64-encoded JSON. Two details matter:

- `index.action` answers with a redirect. The script does not follow it, because following it invalidates the cookie.
- The cookie's path is `/vcf-operations`, not `/ui`, so the script searches all of the session's cookies for it.

### 3. Upload

These are the requests the UI makes for **Administration** > **Integrations** > **Repository** > **Add**. [PAK install: requests made by the UI](pak-install-requests.md) records them in full.

- `ignoreSignatureChecking=true`: the pak is unsigned.
- `forceUpload=true`: installs even when the same version is already installed.
- `forceContent=false`: the value the UI sent in the recorded install.

The upload's response gives the `pakId`, such as `iSDKvCommunity-042` for version 0.4.2, which step 6 uses. The server reports no progress during the upload, so the script prints nothing until it returns.

### 4 and 5. Install

The script reads the EULA, as the UI does, and then starts the install. Accepting the EULA sends nothing to the server. `install` takes no pak ID: the server installs what this session uploaded.

### 6. Wait

The script reads the pak's status from the admin API every 10 seconds and prints each answer. The overall status stays `CANDIDATE` while the pak moves through these states, and becomes `COMPLETED` at the end:

| State | Seen at |
| :--- | :--- |
| `PREAPPLY_VALIDATED` | 0:59 |
| `VALIDATED` | 1:11 |
| `APPLIED_ADAPTER_PRE_SCRIPT` | 1:23 to 4:00, the longest step |
| `APPLIED_ADAPTER` | 4:13 |
| `APPLIED_AND_CLEANED`, then `COMPLETED` | 4:26 to 4:38 |

The script stops at `COMPLETED`, `FAILED` or `CANCELED`. For anything but `COMPLETED`, it prints the server's `failed_details` and exits `1`. On a cluster with more than one node, each line lists every node.

## Design decisions

**The UI requests are used for the upload and install.** The admin API (CaSA) has a documented upload and install, `POST /casa/upgrade/cluster/pak/reserved/operation/upload` and then `.../<pakId>/operation/install`, which needs no CSRF token. But it rejects an unsigned pak on upload with `pak_manager.pakfile.no_signature`, and has no option to skip the check. Only the UI's upload takes `ignoreSignatureChecking`. If the pack is ever signed, the admin API is the simpler route.

**The admin API is used for the status.** The UI has its own status calls, but the author of another open-source installer, [vcf-content-factory](https://github.com/sentania-labs/vcf-content-factory), found that `getLatestInstalledSolutionStatuses` never reaches a final state on 9.0.2. The admin API's status call gives each node's state and a clear final status.

**The UI is not driven in a browser.** An earlier install was done that way, but a person still had to pick the file in the operating system's file dialog, so it could not run unattended. Sending the UI's own requests needs no browser and no person.

**Alternatives not taken:**

- Signing the pak. That needs a certificate VCF Operations trusts, which a community pack does not have.
- Turning on Allow Unsigned PAK Installation from the script. The script does not change security settings: if the setting is off, the upload fails and a person turns it on.

## Troubleshooting

| Message | Cause | Fix |
| :--- | :--- | :--- |
| `UI login failed` | Wrong password, or the account is not a local account | Check `.secrets/vcf-ops.xml`. Use the local `admin` account. |
| `Another pak install is already running` | An install from the UI, or an earlier run, is still going | Wait for it to finish. Check under **Administration** > **Integrations** > **Repository**. |
| `Upload failed` with `unsigned_pak_installation.not.allowed` | Allow Unsigned PAK Installation is off | Turn it on in `/admin` > **Administrator Settings** > **Security Settings**. |
| `No pak for version …` | Nothing built for the `manifest.txt` version | Run `pwsh tools/build/build.ps1`, or pass `-Pak`. |
| Step 6 times out | The install is slow or stuck | Check the pak's status in **Administration** > **Integrations** > **Repository** before you run the script again. |

After an upgrade, the Adapter Instances often stop collecting until their collection is restarted: see [After an Upgrade: Restart Collection](../../docs/installation-guide/installation.md#after-an-upgrade-restart-collection). This script does not restart them. Run `pwsh tools/restart/restart.ps1`, wait one collection cycle, and then run `pwsh tools/validate/validate.ps1 -ExpectedVersion <version>`.

## Running it from an AI coding assistant

An assistant such as Claude Code runs this script directly, as one step of the build, install, restart and validate process, without asking a person to type or run anything ([CLAUDE.md](../../CLAUDE.md)). If the platform blocks the script, for example because it installs an unsigned pak with signature checking off, the assistant reports the block and stops. It does not work around it.
