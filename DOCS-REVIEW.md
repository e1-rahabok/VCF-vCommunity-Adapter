# Docs Review: Continuation Plan

> **Instructions for Claude Code (laptop):** Read this whole file first.
> Then continue the documentation review it describes.
>
> 1. Do not edit anything until the user confirms which items to apply. Ask which items, using the status column below.
> 2. Apply only the items the user approves. Keep each edit minimal and match the surrounding style.
> 3. Do not change code under `Management Pack/app`. Doc-only work.
> 4. Verify after editing:
>    - `python tools/check-docs/check_links.py` must print `0 broken link(s)`.
>    - From `Management Pack`: `python -m pytest tests`. Report the result.
> 5. Do not commit or push unless the user asks.
> 6. When an item is done, change its status to `done` in this file.
> 7. Do not add any model name or attribution to commits, code, or docs.

## Status key

- `proposed`: found in review, not yet approved.
- `approved`: user approved, not yet applied.
- `done`: applied and verified.
- `question`: needs a user answer first.

## Doc map (top down)

- `README.md`: pitch, use cases, dashboards, reports, links.
- `CONTRIBUTING.md`, `CLAUDE.md`: contributor rules.
- `docs/README.md`: documentation index and overview.
- `docs/concepts/`: capacity model, KPI scoring.
- `docs/installation-guide/`: requirements, how it works, install, dark site.
- `docs/configuration-guide/`: policy, Adapter Instance, customization, TLS and security.
- `docs/user-guide/`: Extreme Capacity dashboard.
- `docs/reference/`: metrics and properties list, and `docs/reference/metrics/` (12 metric pages).
- `tools/`: README, plus build, install, validate, importer, and check-docs docs.
- `Management Pack/app/metrics/README.md`: developer guide for metrics.

## Items to review

### High

| # | Status | File | Problem | Proposed update |
| :-- | :-- | :-- | :-- | :-- |
| H1 | proposed | `README.md` | Dashboard list names "VM Configuration" and "vSphere Cluster Capacity". No such files exist in `Management Pack/content/dashboards/`. "Extreme Capacity" is missing. | List the real dashboard files: Cluster Performance 2.0, Critical Business Applications, ESXi Configuration 2.0, Extreme Capacity, VCF Management Service, VM Capacity 2.0, VM Performance 2.0, VM Storage Configuration, vSphere Cluster Configuration 2.0, vSphere Network Configuration 2.0, vSphere Resource Management. |
| H2 | question | `README.md` | Badges and the Super Metrics link use `github.com/vmbro/...`. Repo and other docs use `e1-rahabok/...`. | Ask the user which org is canonical. Then update all links. |
| H3 | question | `docs/README.md` | "What it collects" says "VM snapshot count". No code collects it (checked `Management Pack/app`). | Ask: remove the claim, or add a collector? Default: remove. |
| H4 | question | `docs/README.md` | "A full collection cycle stays under 5 minutes at 1,500+ hosts and 15,000+ VMs." No evidence in repo. | Ask the user to confirm or remove. |
| H5 | proposed | `docs/reference/metrics-and-properties.md` | Top note says Guest OS properties are not included. They are in code: `Guest OS\|Operating System` (`properties/vm/vmOSInformation.py`) and `Guest OS\|Services:<name>` (`properties/vm/vmService.py`). | Remove the note. Add rows: OS Name, OS Version, OS BuildNumber, OS Architecture, OS Last Boot Up Time, OS Release ID (Operating System). Add rows: Service Name, Service Status, Service Start Type (Services, instanced by service display name). Mention Windows Event Logs are events, not properties. |
| H6 | proposed | `docs/reference/metrics-and-properties.md` | Cluster section header says 54 items. Table has 58 rows. Footer says "188 template rows". Table has 206 rows. | Recount and fix both numbers. Or remove the numbers. |
| H7 | proposed | `CONTRIBUTING.md` | "Property Contribution" section is unfinished. It ends with "called ___". | Finish the sentence and steps, or remove the section. Ask the user which. |

### Medium

| # | Status | File | Problem | Proposed update |
| :-- | :-- | :-- | :-- | :-- |
| M1 | proposed | `docs/README.md` | Contents list omits the 12 metric pages. CONTRIBUTING requires every new page in the index. | Add the metric pages, or one line that links to `reference/metrics/README.md` and lists them there. |
| M2 | proposed | `docs/reference/metrics/README.md` | No entry for VM Guest OS KPI (covered only in `vm-performance.md`). DRS Score has no page (only in the properties list). | Add a line for each, linking to where it is described. Ask whether DRS Score needs its own page. |
| M3 | proposed | `Management Pack/app/metrics/README.md` | "What is in this folder" table omits `vm/vm_guest_os_kpi.py`. | Add a row: VM Guest OS KPI, average of VM Performance and Guest OS Performance. |

### Low

| # | Status | File | Problem | Proposed update |
| :-- | :-- | :-- | :-- | :-- |
| L1 | proposed | `docs/configuration-guide/customization.md` | Thin. Does not say which files can be cloned. | List the config files that can be cloned: ESXi advanced settings, ESXi packages, VM advanced parameters, VM options, Windows services, Windows event logs. |
| L2 | proposed | `docs/installation-guide/dark-site.md` | Example image tag is `0.2.0_…`. Current build is `0.4.2`. | Update the example tag, or label it as an example. |
| L3 | proposed | `docs/reference/metrics-and-properties.md` | Says super metrics "now use the built-in metric". Some dashboard and report text still says "vSphere VM Performance" or "vSphere VM Memory Zip Swap": `content/dashboards/Cluster Performance 2.0.json`, `content/dashboards/VM Performance 2.0.json`, `content/reports/View - Set 3.xml`. | Reword the note to "their dashboards and reports use the built-in metric", or flag the descriptions to the content owner. Do not edit content JSON or XML without approval. |

## Checked and current (no change)

- `docs/configuration-guide/adapter-instance.md`: settings and defaults match `adapter.py`.
- `docs/configuration-guide/policy.md`: correct.
- `docs/installation-guide/system-requirements.md`: 8.18 matches `manifest.txt`.
- `docs/installation-guide/installation.md`, `tools/install/pak-install-requests.md`: 0.4.1 and 0.4.2 history is dated. Keep.
- `docs/user-guide/extreme-capacity-dashboard.md`: matches the dashboard JSON.
- `docs/concepts/capacity-management.md`: Close for Business rule matches `periodic_cluster_check.decide()`.
- `docs/reference/metrics/vm-performance.md`: 9 sub-metrics and limits match code.
- `tools/README.md`: scripts and parameters match.

## Not reviewed line by line (do a second pass)

- `docs/configuration-guide/tls-and-security.md`
- `docs/installation-guide/dark-site.md` (apart from L2)
- `docs/concepts/kpi-scoring-models.md`
- Formula pages: `cluster-performance`, `cluster-risk`, `cluster-consumption`, `esxi-performance`, `guest-os-performance`, `vm-shares`, `capacity-utilization`, `operational-availability`, `network-speed-degradation`, `vsphere-world-metrics`, `periodic-cluster-check`
- `tools/build/build.md`, `tools/install/install.md`, `tools/validate/validate.md`, `tools/importer/importer.md`
- `SUPPORT.md`, `SECURITY.md`

## Open questions for the user

1. H2: Which GitHub org is canonical, `e1-rahabok` or `vmbro`?
2. H3: Remove the "VM snapshot count" claim, or add a collector?
3. H4: Keep, confirm, or remove the 1,500 hosts and 5 minutes claim?
4. H7: Finish the CONTRIBUTING section, or remove it?
5. M2: Does DRS Score need its own metric page?

## Log

- 2026-10-23: First review pass. Items H1 to L3 recorded. No files changed.
