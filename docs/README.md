# VCF Operations vCommunity Management Pack

The pack collects the ESXi and VM settings that VCF Operations does not collect out of the box, and calculates extra metrics and KPIs. It publishes them onto the existing vCenter objects in VCF Operations, under the `vCommunity|` key prefix.

It is built with the [VCF Operations Integration SDK](https://github.com/vmware/vmware-aria-operations-integration-sdk). The SDK documentation is at [github.com/vmware/vmware-vcf-operations-integration-sdk, docs](https://github.com/vmware/vmware-vcf-operations-integration-sdk/tree/main/docs). It is written for any adapter, so this documentation explains the parts this pack uses, in [The VCF Operations Integration SDK](development-guide/sdk.md). The Management Pack Builder is the quickest way to extend VCF Operations. The SDK gives more: parallel collection at scale, custom properties and metrics, and configuration files that set exactly what is collected.

## Contents

**Concepts**

- [Capacity Management Model](concepts/capacity-management.md): how consumption, contention and risk decide, automatically, whether a cluster can take more VMs.
- [KPI Scoring Models](concepts/kpi-scoring-models.md): three ways to combine colored sub-metrics into one KPI, which fits performance, capacity and availability, and how the pack scores a KPI: its limits, weights, skipped and missing data.
- [Templates and Content Libraries](concepts/templates-and-content-libraries.md): the two kinds of template, VM Template and OVF & OVA Template, and the content library that holds them.

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

- [vSphere Cluster Capacity 2.0 Dashboard](user-guide/vsphere-cluster-capacity-dashboard.md)

**Reference**

- [Metrics and Properties](reference/metrics-and-properties.md): every key the pack publishes, by object type.
- [Metrics](reference/metrics/README.md): how each metric and KPI is calculated, and its known limitations.
- [Text Display Widget](reference/text-display-widget.md): what HTML a Text Display widget keeps and drops, and how to add a page to it.

**Troubleshooting Guide**

For administrators who use the pack: what can go wrong while it runs, and how to find out why.

1. [First Steps](troubleshooting-guide/first-steps.md): five checks, in order, before you ask for help.
2. [Symptoms](troubleshooting-guide/symptoms.md): what you see, why it happens, and what to do.
3. [Configuration Files](troubleshooting-guide/configuration-files.md): what a bad configuration file looks like, and how to fix it.
4. [Log Messages](troubleshooting-guide/log-messages.md): what each message in the adapter log means.

**Development Guide**

For contributors: how the code is organised, what each part does, and how to change it.

1. [Repository Layout](development-guide/repository-layout.md): what every folder and file is, and which ones are not used.
2. [The VCF Operations Integration SDK](development-guide/sdk.md): the parts of the SDK this pack uses, the packaging, and the links to the SDK documentation.
3. [App Folder](development-guide/app-folder.md): the entry points of the adapter, one collection cycle, and why it is built this way.
4. [Collectors](development-guide/collectors.md): one collector per VCF Operations object type.
5. [Metrics Code](development-guide/metrics-code.md): the metric and KPI modules, and how to add or change one.
6. [Properties](development-guide/properties.md): how properties are read and published.
7. [Supporting Code](development-guide/supporting-code.md): reading from VCF Operations, TLS and guest handling, constants and Windows event logs.
8. [Content Folder](development-guide/content-folder.md): dashboards, reports, super metrics, and the configuration files the code reads.
9. [Tests](development-guide/tests.md): the three test layers and the test files.
10. [Template and Content Library Design](development-guide/template-and-library-design.md): the design for showing templates and content libraries in VCF Operations. Built in the code, not yet verified on the test instance.
11. [Future Enhancements](development-guide/future-enhancements.md): metric ideas noted for later, not designed.
12. [Application Review](development-guide/application-review.md): security, reliability, maintainability and repository review of the code at version 0.6.10, with a tracked list of findings.
13. [To Do project](https://github.com/users/e1-rahabok/projects/1): the enhancements still to do, one line each. Broken things are GitHub issues.

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

It also calculates metrics and KPIs, such as Cluster Performance, Cluster Risk and Cluster Consumption. Every key is listed in [Metrics and Properties](reference/metrics-and-properties.md).

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
- Built for large environments: parallel collectors, and careful limits on expensive host calls. The collection time at scale is not yet measured, see [issue #42](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/42).
- Start with a few settings from your hardening guide, and add more over time.

For what the pack is, its features and how to get started, see the main [README](../README.md). For support and licensing, see [Support](../SUPPORT.md) and [License](../LICENSE).
