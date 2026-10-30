# Handover: Business Application super metrics, Tier probe

Temporary note for the Build Laptop. Delete this file once the probe is answered and the decision is done.

## Why

The three Business Application super metrics (Tier, Business Application, Enterprise) are on Container adapter objects. A super metric needs manual enablement in the policy, and the pak installation cannot enable it. Converting them to regular metrics, published by the pack, would make that automatic. The conversion needs the pack to publish on Container `Tier` objects, which is what the probe tests.

## State

- Branch: `probe-business-app-super-metrics` (from `main`, which is at `e3ee617`).
- Manifest version: `0.6.11`. The probe build must not reuse `0.6.10`.
- The probe (`Management Pack/app/metrics/container/tier_probe.py`, its test, and the `adapter.py` wiring) was removed in `39e65d1` and is restored on this branch. It is not in 0.6.10.
- Unit tests: 425 passed, Python 3.12 (the SDK needs 3.9 to 3.12).
- Not done: build, install, live check.

## Steps on the Build Laptop

1. Check out the branch: `git fetch origin && git checkout probe-business-app-super-metrics`.
2. Start Docker Desktop and wait for "Engine running". Check `docker info`.
3. `docker login ghcr.io`, with an account that can write the `vcf-operations-vcommunity` package.
4. Run the unit tests: `python -m pytest tests`, from `Management Pack`.
5. `pwsh tools/build/build.ps1`. It should end with `Built ... vCommunity_0.6.11.pak`.
6. Install with the UI, or `pwsh tools/install/install.ps1` if the Build Laptop has `.secrets/vcf-ops.xml`.
7. `pwsh tools/restart/restart.ps1`, then wait one collection cycle (about 5 minutes).
8. Check the probe on the Tier objects. Expected: the metric `vCommunity|Tier Probe|Probe Value` with value 42 on each Tier (LLM, DB, Front-end, Web).
9. Send the result back to the session that wrote this file. Include the Tier results, and the install log lines if the probe is missing.

## The decision after the probe

- **Value 42 on the Tier objects:** convert the three super metrics to regular metrics.
  - Tier: average of `vCommunity|VM Guest OS KPI` over the Tier's VMs. Publish nothing when no VM has a value (no data, not 0).
  - Business Application: the existing formula, `max(K8S Namespace Performance, min over tiers)`, with no-data handling.
  - Enterprise: average over Business Applications, with no-data handling.
  - Remove the probe in the same change.
  - Update `content/supermetrics` (remove the three files), the reference pages, and `validate.ps1` (add a check for these objects).
- **No value:** the platform does not accept pack metrics on another adapter's objects. Keep the super metrics. Fix their 0-for-no-data behaviour in the formulas. Remove the probe.

## What was found on the test instance (read-only)

- Tier LLM: its VM `moltbot23` is powered off (no KPI for about 161 h). Tier value 0.
- Tier Front-end: its VM `vcf-m02-edge02` is powered off (no KPI for about 276 h). Tier value 0.
- Tier DB: no VMs linked. Tier value 0.
- Tier Web: VM `sun05-webmin01` is on. Tier value matches the VM KPI (about 99.9).
- Business Applications (AI Chatbot, Internet Banking) and Enterprise: 0, because each takes a minimum over its tiers.
- `sun05-webmin01` exists twice on the instance, one powered on and one off.
- Standard validation on 0.6.10 passed (16 pass, 1 warn, 0 fail). It does not check Business Applications. It samples the first 5 VMs per type, so it missed this.

## Notes

- The Windows venv for the tests is at `C:/Users/iwan rahabok/.vcf-venv` on the session laptop. It is not in the repo.
- Only one branch is in use. Do not add side branches.
