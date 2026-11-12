# VCF Operations vCommunity Management Pack

The pack collects ESXi, VM and vCenter settings that VCF Operations does not collect by default, and calculates extra metrics and KPIs. It publishes them on the existing vCenter objects in VCF Operations under the `vCommunity|` key prefix. It also creates three object types of its own for content libraries and VM templates.

The pack is built with the [VCF Operations Integration SDK](https://github.com/vmware/vmware-aria-operations-integration-sdk). The [SDK documentation](https://github.com/vmware/vmware-vcf-operations-integration-sdk/tree/main/docs) covers any adapter. [The VCF Operations Integration SDK](development-guide/sdk.md) describes the parts this pack uses. Compared with the Management Pack Builder, the SDK supports parallel collection, calculated metrics and KPIs, and configuration files that control what is collected.

## Contents

**Concepts**

- [Capacity Management Model](concepts/capacity-management.md): how consumption, contention and risk decide whether a cluster can take more VMs.
- [KPI Scoring Models](concepts/kpi-scoring-models.md): three ways to combine colored sub-metrics into one KPI, which one suits performance, capacity and availability, and how the pack scores a KPI (limits, weights, skipped and missing data).
- [Templates and Content Libraries](concepts/templates-and-content-libraries.md): VM templates, OVF and OVA templates, and the content libraries that hold them.

**Installation Guide**

1. [System Requirements](installation-guide/system-requirements.md): platform versions, registry access and accounts.
2. [How It Works](installation-guide/how-it-works.md): the Cloud Proxy runs the pack as a container.
3. [Installation](installation-guide/installation.md): install or upgrade the `.pak` file.
4. [Dark Site](installation-guide/dark-site.md): use a private registry when the Cloud Proxy has no internet access.

**Configuration Guide**

1. [Policy](configuration-guide/policy.md): activate the host network metrics the pack needs. They are off by default.
2. [Adapter Instance](configuration-guide/adapter-instance.md): connect to a vCenter, and the advanced settings.
3. [Customization](configuration-guide/customization.md): choose what each Adapter Instance collects.
4. [Business Applications](configuration-guide/business-applications.md): create the applications that the Business Application Performance metrics are calculated for.
5. [Summary Dashboards](configuration-guide/summary-dashboards.md): replace the built-in Summary tab of an object type with a dashboard, including the six Summary dashboards the pack ships.
6. [TLS and Security Settings](configuration-guide/tls-and-security.md): certificate checks, what runs inside Windows VMs, the registry and accounts.
7. [Bulk Adapter Instance Importer](../tools/importer/importer.md): create many Adapter Instances from a CSV file.

**User Guide**

- [Included Content](user-guide/included-content.md): the dashboards, reports, views, alerts and super metrics in the pack, and which ones you have to turn on.
- [vSphere Cluster Capacity 2.0 Dashboard](user-guide/vsphere-cluster-capacity-dashboard.md)

**Reference**

- [Metrics and Properties](reference/metrics-and-properties.md): every key the pack publishes, by object type.
- [Metrics](reference/metrics/README.md): how each metric and KPI is calculated, and its known limitations:
  [Business Application Performance](reference/metrics/business-application-performance.md),
  [Cluster Consumption](reference/metrics/cluster-consumption.md),
  [Cluster Performance](reference/metrics/cluster-performance.md),
  [Cluster Risk](reference/metrics/cluster-risk.md),
  [ESXi Performance](reference/metrics/esxi-performance.md),
  [Guest OS Performance](reference/metrics/guest-os-performance.md),
  [Network Speed Degradation](reference/metrics/network-speed-degradation.md),
  [Operational Availability](reference/metrics/operational-availability.md),
  [Periodic Cluster Check](reference/metrics/periodic-cluster-check.md),
  [VM Performance](reference/metrics/vm-performance.md),
  [VM Shares](reference/metrics/vm-shares.md),
  [vSphere World Cluster Metrics](reference/metrics/vsphere-world-metrics.md).
- [Text Display Widget](reference/text-display-widget.md): which HTML a Text Display widget keeps and drops, and how to add a page to one.

**Troubleshooting Guide**

For administrators: what can go wrong while the pack runs, and how to find the cause.

1. [First Steps](troubleshooting-guide/first-steps.md): five checks to run, in order, before you ask for help.
2. [Symptoms](troubleshooting-guide/symptoms.md): what you see, why it happens, and what to do.
3. [Configuration Files](troubleshooting-guide/configuration-files.md): what a bad configuration file looks like and how to fix it.
4. [Log Messages](troubleshooting-guide/log-messages.md): what each message in the adapter log means.
5. [Dashboards After an Install](troubleshooting-guide/dashboards-after-install.md): why a dashboard shows `Section` or empty widgets for a while, and what to do.

**Development Guide**

For contributors: how the code is organized, what each part does, and how to change it.

1. [Repository Layout](development-guide/repository-layout.md): every folder and file, and which ones are not used.
2. [The VCF Operations Integration SDK](development-guide/sdk.md): the parts of the SDK this pack uses, packaging, and links to the SDK documentation.
3. [App Folder](development-guide/app-folder.md): the entry points of the adapter, one collection cycle, and the design behind it.
4. [Collectors](development-guide/collectors.md): the collection jobs and the objects each one publishes.
5. [Metrics Code](development-guide/metrics-code.md): the metric and KPI modules, and how to add or change one.
6. [Properties](development-guide/properties.md): how properties are read and published.
7. [Supporting Code](development-guide/supporting-code.md): reading from VCF Operations, TLS and guest handling, collection health, constants and Windows event logs.
8. [Content Folder](development-guide/content-folder.md): dashboards, reports, super metrics, alerts, and the configuration files the code reads.
9. [Tests](development-guide/tests.md): the test layers and the test files.
10. [Template and Content Library Design](development-guide/template-and-library-design.md): how the Content Library, Library Item and VM Template objects are built. Shipped in 0.6.6. The library links were checked on the test instance in 0.7.3. The VM Template objects have no live check yet.
11. [Pak Summary Binding](development-guide/pak-summary-binding.md): binding a dashboard to an object type's Summary tab from the pak, what `mp-build` allows, and what was tested.
12. [Future Enhancements](development-guide/future-enhancements.md): metric ideas noted for later, not designed yet.
13. Engineering reviews:
    - [29 Oct 2026 Review](development-guide/engineering-review/2026-10-29-review.md): the review of version 0.6.12, with the scorecard and the findings.
    - [29 Oct 2026 Completed](development-guide/engineering-review/2026-10-29-completed.md): the decision and action for each finding.
    - [30 Oct 2026 Review](development-guide/engineering-review/2026-10-30-review.md): the re-score after the 0.7.0 fixes, with the verdict on each rejection and deferral, and new findings.

Planned enhancements are on the [To Do project](https://github.com/users/e1-rahabok/projects/1), one line each. Bugs are [GitHub issues](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues).

## Why the pack exists

Most organizations that run vSphere have a standard for their ESXi and VM settings. It can be a formal config workbook, a security hardening guide, or an unwritten convention. VMware and Broadcom hardening guides, KB articles and best-practice papers name specific ESXi advanced system settings and VM advanced parameters, and wrong values cause instability, poor performance or security exposure.

Writing the standard down is usually done. Knowing whether the environment still matches it is harder, because configuration drifts:

- A setting is changed during troubleshooting and never changed back.
- A new host is built without the standard advanced settings.
- A VM template moves away from the security baseline over successive clones.

None of these raise an alert. They show up later as an incident, an audit finding, or two "identical" clusters that behave differently. Health checks, workbooks and hardening guides describe the expected state. They don't show the current state of every host and VM.

## From config workbook to continuous compliance

Many organizations keep a **config workbook**: the expected ESXi and VM settings, agreed for lab and production. They check it in two ways:

- A **periodic best-practice health check**, run now and then.
- **Continuous compliance** in VCF Operations, which compares the running environment with the workbook and flags drift.

Continuous compliance can only check data that VCF Operations collects, and by default it does not collect ESXi advanced system settings or VM advanced parameters. The pack collects them. List the settings from your workbook in the pack's configuration files, and they become properties in VCF Operations that compliance rules, dashboards and alerts can use. The workbook stays the source of truth.

## Use cases

| Use case | What it looks like |
| :--- | :--- |
| **Configuration drift detection** | A changed advanced setting, VM parameter or cluster setting shows up in the next collection cycle, not months later in a root-cause analysis. |
| **Security hardening** | Track the ESXi and VM settings your hardening guide names, continuously instead of at point-in-time assessments. |
| **One standard across environments** | Compare lab with production, or site A with site B, against one baseline. Each Adapter Instance can use its own configuration files: see [Customization](configuration-guide/customization.md). |
| **Feeding compliance** | VCF Operations compliance templates can only check data that is collected. The pack collects it. |
| **Faster root cause** | Configuration history sits next to the performance data, so "what changed" is a query. |
| **Evidence between formal reviews** | The VMware Health and Security Toolkit (HST) gives a deep assessment with your VCF TAM, typically every quarter or year. The pack covers the time in between. |

## What it collects

You choose these with configuration files:

- **ESXi advanced system settings.**
- **ESXi software packages (VIBs)**: name, version, vendor and acceptance level.
- **VM advanced parameters**: `.vmx` settings.
- **VM options**: fields such as boot options, firmware type and hardware version.
- **Windows services and event logs**: optional, through VMware Tools.

These are collected without configuration:

- **Cluster HA, DRS, DPM and EVC settings.**
- **Host details**: licensing, install date, uplinks and storage adapters, and other properties the vCenter adapter does not collect.
- **VM details**: disks, shares and configuration flags.
- **vCenter settings** and the vCenter certificate.
- **Content libraries, library items and VM templates.**

The pack also calculates metrics and KPIs, such as Cluster Performance, Cluster Risk and Cluster Consumption. Every key is listed in [Metrics and Properties](reference/metrics-and-properties.md).

### Security hardening areas it can track

| Concern | Where | What the pack collects |
| :--- | :--- | :--- |
| Managed Object Browser (MOB) left enabled | vCenter | `vCommunity\|Configuration\|Enable MOB` |
| VM isolation: copy and paste, drag and drop, disk shrink | VM advanced parameters | Any `isolation.tools.*` or `isolation.device.*` key you add to your clone of `vm_advanced_parameters.xml` |
| Remote logging | ESXi advanced settings | Any `Syslog.global.*` key you add to your clone of `esxi_advanced_system_settings.xml` |
| Account lockout | ESXi advanced settings | `Security.AccountLockFailures`, `Security.AccountUnlockTime` |
| Shell and DCUI timeout | ESXi advanced settings | `UserVars.ESXiShellTimeOut`, `UserVars.ESXiShellInteractiveTimeOut`, `UserVars.DcuiTimeOut` |
| VIB acceptance level | ESXi software packages | `vCommunity\|Configuration\|Packages:<name>\|Acceptance Level` |
| Event and task retention | vCenter | `vCommunity\|Configuration\|Database\|Event retention (days)`, `Task retention (days)` |

The table is not tied to one hardening guide. Any ESXi advanced setting or VM advanced parameter your guide names can be tracked.

## How it fits with other tools

The pack adds data. It does not replace these:

- **HST**: deep, periodic assessments. The pack covers the time between them.
- **VCF Operations compliance templates**: compare expected with actual values. They need the data the pack collects.
- **Your config workbook**: remains the source of truth. The pack makes it possible to check it continuously.

## Cost and scale

- The pack is free.
- It installs like any VCF Operations Management Pack. Nothing is installed on ESXi and nothing changes in vCenter. The Windows checks are optional and need no agent.
- Collection runs in parallel jobs, and the slow per-host calls are limited to the data you choose. Collection time at large scale has not been measured yet, see [issue #42](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/42).
- Start with a few settings from your hardening guide and add more over time.

For an overview of features and how to get started, see the main [README](../README.md). For help, see [Support](../SUPPORT.md).
