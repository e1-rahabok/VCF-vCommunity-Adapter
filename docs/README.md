# VCF Operations vCommunity Management Pack

The pack collects the ESXi and VM settings that VCF Operations does not collect out of the box, and calculates extra metrics and KPIs. It publishes them onto the existing vCenter objects in VCF Operations, under the `vCommunity|` key prefix.

It is built with the [VCF Operations Integration SDK](https://github.com/vmware/vmware-aria-operations-integration-sdk). The Management Pack Builder is the quickest way to extend VCF Operations. The SDK gives more: parallel collection at scale, custom properties and metrics, and configuration files that set exactly what is collected.

## Contents

**Concepts**

- [Capacity Management Model](concepts/capacity-management.md): how consumption, contention and risk decide, automatically, whether a cluster can take more VMs.
- [KPI Scoring Models](concepts/kpi-scoring-models.md): three ways to combine colored sub-metrics into one KPI, and which fits performance, capacity and availability.

**Installation Guide**

1. [System Requirements](installation-guide/system-requirements.md): platform versions, registry access, accounts.
2. [How It Works](installation-guide/how-it-works.md): the Cloud Proxy runs the pack as a container.
3. [Installation](installation-guide/installation.md): install the PAK file.
4. [Dark Site](installation-guide/dark-site.md): use a private registry when the Cloud Proxy has no internet access.

**Configuration Guide**

1. [Policy](configuration-guide/policy.md): activate the metrics the pack needs. They are off by default.
2. [Adapter Instance](configuration-guide/adapter-instance.md): connect to a vCenter, advanced settings.
3. [Customization](configuration-guide/customization.md): choose what each Adapter Instance collects.
4. [TLS and Security Settings](configuration-guide/tls-and-security.md): certificate checks, what runs inside Windows VMs, registry, accounts.
5. [Bulk Adapter Instance Importer](../tools/importer/importer.md): create many Adapter Instances from a CSV file.

**User Guide**

- [Extreme Capacity Dashboard](user-guide/extreme-capacity-dashboard.md)

**Reference**

- [Metrics and Properties](reference/metrics-and-properties.md): every key the pack publishes, by object type.
- [Metrics](reference/metrics/README.md): how each metric and KPI is calculated, and its known limitations.

Planned work is tracked in [GitHub Issues](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement), not here.

## The problem

Every organization running vSphere has a standard: the ESXi and VM settings that should be true on every host and every VM. It may be a formal config workbook, a security hardening guide, or "how we have always done it". VMware/Broadcom hardening guides, KB articles and best-practice papers name specific ESXi Advanced System Settings and VM Advanced Parameters. Getting them wrong causes instability, slow performance or security exposure.

Defining the standard is not the problem. Knowing, at any moment, whether the environment matches it is. Configuration drifts quietly:

- A setting is changed during troubleshooting and never reverted.
- A new host is built without the standard advanced settings.
- A VM template drifts from the security baseline over successive clones.

None of this raises an alert. It shows up later as an incident, an audit finding, or two "identical" clusters that behave differently. Health checks, workbooks and hardening guides say what should be true. They do not say what is true now, everywhere.

## From config workbook to continuous compliance

Many organizations keep a **config workbook**: the baseline of expected ESXi and VM settings, agreed across lab and production. On top of it they run two kinds of check:

- A **periodic best-practice health check**, run occasionally.
- **Continuous compliance** in VCF Operations: the running environment compared with the workbook, drift flagged automatically.

The second only works on data VCF Operations collects. Out of the box, it does not collect ESXi Advanced System Settings or VM Advanced Parameters. So the workbook has nothing to be checked against.

The pack closes this gap. Point its configuration files at the settings the workbook defines, and they become live properties in VCF Operations, ready for compliance rules, dashboards and alerts. The workbook stays the source of truth.

## Use cases

| Use case | What it looks like |
| :--- | :--- |
| **Configuration drift detection** | See a changed advanced setting, VM parameter or cluster setting when it happens, not months later in a root-cause analysis. |
| **Security hardening** | Track the ESXi and VM settings your hardening guide names, continuously, instead of only at point-in-time assessments. |
| **Same standard across environments** | Compare lab with production, or site A with site B, against one baseline. Configuration files can be set per environment: see [Customization](configuration-guide/customization.md). |
| **Feeding compliance** | VCF Operations Compliance Templates can only check data that is collected. The pack collects it. |
| **Faster root cause** | "What changed" is a dashboard query, not a guess. Configuration history sits next to the rest of the VCF Operations data. |
| **Evidence between formal reviews** | The VMware Health and Security Toolkit (HST) gives a deep assessment, typically quarterly or yearly, with your VCF TAM. The pack covers the time in between. |

## What it collects

All of it is set by configuration files:

- **ESXi Host Advanced System Settings**: the settings you choose.
- **ESXi Host Software Packages (VIBs)**: name, version and vendor of the packages you choose.
- **VM Advanced Parameters**: the `.vmx` settings you choose.
- **VM Options**: fields such as boot options, firmware type and hardware version.
- **Cluster HA, DRS and EVC settings.**
- **Windows Services and Event Logs**: optional, agentless through GuestAPI.
- **VM snapshot count**, and other properties missing from the default inventory.

It also calculates metrics and KPIs, such as Cluster Performance, Cluster Risk, Cluster Consumption and Capacity Utilization. Every key is listed in [Metrics and Properties](reference/metrics-and-properties.md).

### Security hardening areas it can track

| Concern | Where | What the pack collects |
| :--- | :--- | :--- |
| Managed Object Browser (MOB) left enabled | vCenter | `vCommunity\|Configuration\|Enable MOB` |
| VM isolation: copy and paste, drag and drop, disk shrink | VM Advanced Parameters | Any `isolation.tools.*` or `isolation.device.*` key added to `vm_advanced_parameters.xml` |
| Remote logging | ESXi Advanced Settings | Any `Syslog.global.*` key added to `esxi_advanced_system_settings.xml` |
| Account lockout | ESXi Advanced Settings | `Security.AccountLockFailures`, `Security.AccountUnlockTime` |
| Shell and DCUI timeout | ESXi Advanced Settings | `UserVars.ESXiShellTimeOut`, `UserVars.ESXiShellInteractiveTimeOut`, `UserVars.DcuiTimeOut` |
| VIB acceptance level | ESXi Software Packages | `vCommunity\|Configuration\|Packages:<name>\|Acceptance Level` |
| Event and task retention | vCenter | `vCommunity\|Configuration\|Database\|Event retention (days)`, `Task retention (days)` |

This is not a mapping to one hardening guide. If your guide names an ESXi advanced setting or a VM advanced parameter, the pack can track it.

## How it fits with what you have

It replaces nothing. It fills one gap:

- **HST**: deep, periodic assessments. The pack fills the time between them.
- **VCF Operations Compliance Templates**: define expected against actual. They need the data the pack collects.
- **Your config workbook**: stays the source of truth. The pack makes it checkable, all the time.

## Cost and scale

- **Free**, community licensed: see [License](../LICENSE).
- Installs like any VCF Operations Management Pack. No agent on ESXi, no change to vCenter. Guest OS features are optional and agentless.
- Built for large environments: parallel collectors, and careful limits on expensive host calls. A full collection cycle stays under 5 minutes at 1,500+ hosts and 15,000+ VMs.
- Start with a few settings from your hardening guide, and add more over time.

## Community

A free Management Pack developed by [Onur Yuzseven](https://www.linkedin.com/in/oyuzseven/) as a contribution to the vCommunity (VMUG, vExpert, VCP). It is not an official VMware/Broadcom project and has no VMware GSS support: see [Support](../SUPPORT.md) and [License](../LICENSE). Dashboards, reports and super metrics from the community are listed in the main [README](../README.md).
