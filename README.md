[![Release](https://img.shields.io/github/v/release/e1-rahabok/VCF-vCommunity-Adapter)](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/releases)
[![Files](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fe1-rahabok%2FVCF-vCommunity-Adapter%2Fbadges%2Ffiles.json)](https://github.com/e1-rahabok/VCF-vCommunity-Adapter)
[![Lines](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fe1-rahabok%2FVCF-vCommunity-Adapter%2Fbadges%2Flines.json)](https://github.com/e1-rahabok/VCF-vCommunity-Adapter)
[![Repo size](https://img.shields.io/github/repo-size/e1-rahabok/VCF-vCommunity-Adapter)](https://github.com/e1-rahabok/VCF-vCommunity-Adapter)

# VCF Operations vCommunity Management Pack

A free Management Pack for VCF Operations. It collects ESXi, VM and vCenter settings that VCF Operations does not collect by default, and it calculates capacity and performance scores for clusters, hosts and VMs. Everything it publishes appears on the vCenter objects you already monitor, under the `vCommunity|` prefix.

The documentation starts at [docs/README.md](docs/README.md).

## Why use it

- **Capacity decisions per cluster.** Each cluster gets a Cluster Performance, Cluster Risk and Cluster Consumption score, plus a Close for Business value that says whether it should take new VMs.
- **Scores you can trace.** Each KPI is built from sub-metrics that are published next to it, so you can see which one drives the score.
- **Configuration drift as data.** A changed host setting, VM parameter or cluster setting becomes a property you can alert on, report on and check with a compliance template.
- **Your hardening guide or config workbook, checked continuously** instead of once per audit.
- **Agentless.** Nothing is installed on ESXi or vCenter. The optional Windows checks run through VMware Tools.

## Features

- **Properties** on ESXi hosts, VMs, clusters, datastores and vCenter: advanced settings, VM options, software packages (VIBs), licensing, HA, DRS, DPM and EVC settings, and vCenter certificate tracking. All keys are in [Metrics and Properties](docs/reference/metrics-and-properties.md).
- **KPIs**, each a 0 to 100 score built from visible sub-metrics: Cluster Performance, Cluster Risk, Cluster Consumption, ESXi Performance, VM Performance, Guest OS Performance, and Business Application Performance for Tiers, Business Applications and the Enterprise. See [KPI Scoring Models](docs/concepts/kpi-scoring-models.md).
- **Other metrics**: Operational Availability, Network Speed Degradation, VM shares, and counts such as resource pools, port groups and VMware Tools status.
- **Periodic Cluster Check**: a Close for Business value per cluster, once per period you choose, based on the worst part of that period. See [Periodic Cluster Check](docs/reference/metrics/periodic-cluster-check.md).
- **vSphere World summaries** across all vCenters, such as the worst and the worst 10 percent of clusters.
- **Content library objects**: Content Library, Library Item and VM Template, created by the pack with their own properties and metrics.
- **Windows checks**: services, OS information and event logs, read through VMware Tools. Optional, and off by default.
- **Collection health**: a warning count and the first warning of each cycle on the vCenter object, with an alert.
- **Dashboards, reports, views and alerts**, listed in [Included Content](docs/user-guide/included-content.md).
- **Configurable**: each list of settings to collect is an XML file that you clone per environment. See [Customization](docs/configuration-guide/customization.md).

<details>
<summary>Dashboards included</summary>

New dashboards: Critical Business Applications, vSphere Resource Management, VM Storage Configuration, VCF Management Service, Overall Daily Check.

New versions of existing dashboards: VM Capacity (new), VM Performance 2.0, vSphere Cluster Performance 2.0, vSphere Cluster Capacity 2.0, vSphere Cluster Configuration 2.0, ESXi Configuration 2.0, vSphere Network Configuration 2.0.

Summary dashboards for six object types (the four folder types, Distributed Switch and Distributed Port Group). They are off until you bind them, see [Summary Dashboards](docs/configuration-guide/summary-dashboards.md).

The VCF Optimization Assessment report set: 5 PDF reports and 11 CSV exports, with the dashboards they are built from.

The alerts and the two super metrics are off after install. [Included Content](docs/user-guide/included-content.md) says how to turn them on.

A dashboard for Microsoft Windows services is available from [Dale Hassinger](https://www.vcrocs.info/vcommunity-mp-windows-servers-services/). The pack does not ship one.

</details>

## Get started

1. Check the [system requirements](docs/installation-guide/system-requirements.md). If the Cloud Proxy has no internet access, follow the [dark site](docs/installation-guide/dark-site.md) steps.
2. Download the `.pak` file from [Releases](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/releases) and [install](docs/installation-guide/installation.md) it.
3. [Activate the policy](docs/configuration-guide/policy.md) metrics the pack needs. Some are off by default.
4. Create an [Adapter Instance](docs/configuration-guide/adapter-instance.md) for each vCenter, or use the [bulk importer](tools/importer/importer.md) for many.
5. Choose what to collect: [Customization](docs/configuration-guide/customization.md).

If something does not work, start with the [Troubleshooting Guide](docs/troubleshooting-guide/first-steps.md).

## Built with

The pack is written in Python with the [VCF Operations Integration SDK](https://github.com/vmware/vmware-vcf-operations-integration-sdk/tree/main/docs). It reads vCenter with pyVmomi and the vSphere Automation API, and reads VCF Operations through its REST API. The [Development Guide](docs/development-guide/repository-layout.md) explains the code and how to change it.

## Companion site: isvara.io

[isvara.io](https://isvara.io) complements this adapter. Its content (metrics, dashboards, alerts, properties and more) and this adapter are both documented in the **Private Cloud Management** book, 5th edition, which you can download from [isvara.io/download](https://isvara.io/download).

The site is built by:

- [Iwan Rahabok](https://www.linkedin.com/in/e1ang/)
- [Samir Roshan](https://www.linkedin.com/in/samirroshan/)
- [Vincent Han](https://www.linkedin.com/in/vincent-han-11298424/)

## Agent E2

(https://github.com/e1-rahabok/agent-e2/tree/main)) complements

## Community and support

- [Contributing](CONTRIBUTING.md): how to help, with or without writing code.
- [Support](SUPPORT.md): how to get help.
- [Security](SECURITY.md): how to report a vulnerability.

This is a free community project from the vCommunity (VMUG, vExpert, VCP). It is not an official VMware or Broadcom product and has no VMware GSS support. Deploy it at your own risk, or ask your VMware TAM or PSO for a custom solution.

## Credits

Built on the work of [Onur Yuzseven](https://www.linkedin.com/in/oyuzseven/), with help from [Mark Arbogast](https://www.linkedin.com/in/mark-arbogast/) and [Robert Mesropyan](https://www.linkedin.com/in/robert-mesropyan/).

[Brock Peterson](https://www.linkedin.com/in/brockpetersonbdcvmw/) wrote a blog series on the pack and its use cases: [part 1](https://www.brockpeterson.com/post/vcommunity-management-pack-for-vcf-operations), [part 2](https://www.brockpeterson.com/post/vcommunity-management-pack-for-vcf-operations-part-2) (Windows checks) and [part 3](https://www.brockpeterson.com/post/vcommunity-management-pack-for-vcf-operations-part-3).

The dashboards, reports and the design of the pack are by [Iwan Rahabok](https://www.linkedin.com/in/e1ang/). His books are available [here](https://broadcom.box.com/v/OpsYourWorld).

To try the pack first, use the VMware Hands-on Lab that [Abhijit Timble](https://www.linkedin.com/in/abhijit-timble-75878514/) set up: [test drive this MP](https://labs.hol.vmware.com/HOL/catalog/lab/26848).
