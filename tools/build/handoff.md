# Handoff: build and install v0.6.0

A temporary instruction for building and installing v0.6.0 on a second machine. Delete this file once v0.6.0 is installed and the lab is back to normal.

Work through the steps in order. Stop at any step that fails, and report the output before going on.

Scope: **build and install only. Do not validate.** Live validation is skipped on purpose, because the lab state below would make it fail.

## Rules for this session

- Do not print, log or commit passwords, tokens, or the contents of `.secrets/`. The `.secrets/` folder is gitignored and must stay that way.
- Do not run `tools/install/install.ps1` yourself. Auto mode blocks it. Give the user the command and wait for them to run it in their own terminal and report the output.
- Do not start the `vCommunity` Adapter Instance. Do not change the account, the vCenter, or the VCF Operations configuration without asking the user first.
- Do not use any vCenter root password from earlier chats. Do not ask for one.
- Do not change the pack's code or docs. If a step fails, report the output and the file, and wait.

## Current state (checked from the lab, read-only)

- **Code:** `main` at `7ae386f` or later, which includes PR #34 (port group and VMware Tools counts). `manifest.txt` says `0.6.0`.
- **vCenter:** up. Login works. Inventory: 1 Datacenter, 1 cluster, 3 hosts, 83 VMs, 20 distributed port groups.
- **vCenter sessions:** about 670, almost all from VCF platform service accounts, all created within the same 30 minutes. None are from this pack. This is a VCF-side issue, to be raised with the VCF administrator. Do not try to fix it from this repository.
- **VCF Operations native VMware adapter:** collecting again.
- **`vCommunity` Adapter Instance:** `STOPPED`. Leave it stopped.
- **Installed pack:** the check did not find a `vCommunity` solution installed. Confirm with the user whether an older version is installed before the install step. An install replaces the installed version.
- **Windows service monitoring and Windows event monitoring** are disabled on the Adapter Instance. Leave them disabled.
- **vCenter `vpxd`:** the services API reports `STOPPED`, but login and inventory work. The services status is not reliable here. Do not act on it.

## Step 1: Get the latest code

```
git checkout main
git pull --ff-only origin main
git status
git log --oneline -1
```

Expected: a clean tree on `main`, at `7ae386f` or later. Report the output.

## Step 2: Unit tests

```
cd "Management Pack"
.venv-test\Scripts\python.exe -m pytest tests -q
```

Expected: 393 passed. Report the last lines of the output.

## Step 3: Link check

From the repository root:

```
python tools/check-docs/check_links.py
```

Expected: `0 broken link(s)`.

## Step 4: Build v0.6.0

From the repository root:

```
pwsh tools/build/build.ps1
```

Expected: the script prints the pak path, such as `Built ...\Management Pack\build\vCommunity_0.6.0.pak`, and exits 0. The version comes from `Management Pack/manifest.txt`, which should read `0.6.0`.

If it fails, read `Management Pack/logs/build.log`, report the last 30 lines, and stop. Do not change `manifest.txt`.

## Step 5: Ask the user to install

Tell the user to run this in their own terminal, from the repository root:

```
pwsh tools/install/install.ps1
```

Say that it replaces any installed `vCommunity` pack, and ask them to confirm first whether an older version is installed. Wait for the user to report the output. Do not run it yourself.

## Step 6: Confirm the install

After the user reports the install finished, confirm the installed version. Use the same API read as the validate script: the installed solution's version must be `0.6.0`. Report what you find.

Do not start the Adapter Instance. Do not run `restart.ps1`, because it starts collection. Do not run `validate.ps1`.

## What to tell the user at the end

- The output of each step, with the pak path and the version.
- Whether the install finished, and the installed version as read in Step 6.
- That the Adapter Instance is still stopped, and that validation has not been run.
- Anything that was not run, and why.
- The next decision for the user: when to start the Adapter Instance, and whether the vCenter session count has settled first.
