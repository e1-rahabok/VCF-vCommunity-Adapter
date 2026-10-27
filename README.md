[![Blog](https://img.shields.io/badge/vSphere%20vCommunity%20Management%20Pack-157BAD)](https://github.com/vmbro/VCF-Operations-vCommunity-Content)
[![MP Version](https://img.shields.io/github/v/release/vmbro/VCF-Operations-vCommunity)](https://badge.fury.io/gh/vmbro%2Fvcf-operations-vcommunity-content)
[![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/vmbro/VCF-Operations-vCommunity/total)](https://github.com/vmbro/VCF-Operations-vCommunity-Content)
[![Blog](https://img.shields.io/github/repo-size/vmbro/vcf-operations-vcommunity-content?style=flat)](https://vmbro.com/)
[![Blog](https://img.shields.io/github/stars/vmbro/vcf-operations-vcommunity-content?style=flat)](https://github.com/vmbro/VCF-Operations-vCommunity-Content/stargazers)

# VCF Operations vCommunity Management Pack

VCF Operations sees your VMware Cloud Foundation estate, but out of the box it misses some ESXi and VM settings that matter for compliance, and it cannot say whether a cluster is full. This free Management Pack fills both gaps. It collects the settings you choose, calculates capacity scores, and publishes everything on the vCenter objects you already monitor, under the `vCommunity|` prefix.

Full documentation starts at [docs/README.md](docs/README.md).

## Why use it

- **Answer capacity questions.** Each cluster gets Cluster Performance, Cluster Risk and Cluster Consumption scores, and a Close for Business value that says whether it can take new VMs.
- **Explain every score.** Each KPI is built from visible sub-metrics, so you see which one is driving it.
- **Stay agentless.** Nothing is installed on ESXi hosts or on vCenter. Windows checks use the vSphere Guest API.
- **Catch configuration drift when it happens.** A changed host setting, VM parameter or cluster setting becomes a property you can alert on, report on and check against a compliance template.
- **Check your standard continuously.** Turn your hardening guide or config workbook into live data, instead of checking it at the next audit.

## Features

- **Properties** on ESXi hosts, VMs, clusters, datastores and vCenter: advanced settings, VM options, software packages (VIBs), licensing, HA, DRS, DPM and EVC, certificate tracking. Every key is listed in [Metrics and Properties](docs/reference/metrics-and-properties.md).
- **Metrics and KPIs**: Cluster Performance, Cluster Risk, Cluster Consumption, VM Performance, Guest OS Performance and ESXi Performance, each scored 0 to 100 from visible sub-metrics. See [KPI Scoring Models](docs/concepts/kpi-scoring-models.md).
- **Periodic Cluster Check**: once per period, a Close for Business value per cluster, with the worst part of the period decided by you. See [Periodic Cluster Check](docs/reference/metrics/periodic-cluster-check.md).
- **Summaries across all vCenters** on the vSphere World object, such as the bottom 10 percent of clusters.
- **Microsoft Windows checks**: services, OS information and event logs, agentless through the Guest API.
- **Dashboards, reports and alerts**, ready to use, listed below.
- **Customizable**: every list of settings is an XML file you clone per environment. See [Customization](docs/configuration-guide/customization.md).

<details>
<summary>Dashboards, reports and super metrics included</summary>

New dashboards: Critical Business Application, vSphere Resource Management, VM Storage Configuration, VCF Management Service, Overall Daily Check.

Enhanced dashboards, replacing the existing ones: VM Configuration, VM Capacity, VM Performance, vSphere Cluster Performance, vSphere Cluster Capacity, vSphere Cluster Configuration, ESXi Configuration, vSphere Network Configuration.

Reports replace all the existing vSphere adapter reports. They were designed as a set, and each one is purpose-built: PDF for reading, CSV for export.

Super metrics are used by the dashboards.Bulk-enable them in the policy after installation.

The Microsoft Windows services dashboard is [Dale Hassinger's](https://www.vcrocs.info/vcommunity-mp-windows-servers-services/). The pack does not ship one.

</details>

## Get started

1. Check the [system requirements](docs/installation-guide/system-requirements.md), and the [dark site](docs/installation-guide/dark-site.md) steps if the Cloud Proxy has no internet access.
2. [Install](docs/installation-guide/installation.md) the PAK file.
3. [Activate the policy](docs/configuration-guide/policy.md) items the pack needs. Some are off by default.
4. Create an [Adapter Instance](docs/configuration-guide/adapter-instance.md) for each vCenter, or use the [bulk importer](tools/importer/importer.md) for many.
5. Choose what to collect: [Customization](docs/configuration-guide/customization.md).

Something not working? Start with the [Troubleshooting Guide](docs/troubleshooting-guide/first-steps.md).

## Built with

The pack is built with the [VCF Operations Integration SDK](https://github.com/vmware/vmware-vcf-operations-integration-sdk/tree/main/docs), in Python, on the VCF Operations API. The [documentation](docs/README.md) explains the parts this pack uses, the code, and how to change it.

## Companion site: isvara.io

[isvara.io](https://isvara.io) complements this adapter. Its content (metrics, dashboards, alerts, properties and more) and this adapter are both documented in the **Private Cloud Management** book, 5th edition. The book is downloadable at [isvara.io/download](https://isvara.io/download).

The site is built by three people:

- [Iwan Rahabok](https://www.linkedin.com/in/e1ang/)
- [Samir Roshan](https://www.linkedin.com/in/samirroshan/)
- [Vincent Han](https://www.linkedin.com/in/vincent-han-11298424/)

## Community and support

- [Contributing](CONTRIBUTING.md): how to help, with or without writing code.
- [Support](SUPPORT.md): what support is, and what is not.
- [License](LICENSE).

This is a free community project from the vCommunity (VMUG, vExpert, VCP). It is not an official VMware or Broadcom product, and it has no VMware GSS support. Deploy it at your own risk, or ask your VMware TAM or PSO for a custom solution.

## Credits

Built on the work of [Onur Yuzseven](https://www.linkedin.com/in/oyuzseven/), assisted by [Mark Arbogast](https://www.linkedin.com/in/mark-arbogast/) and [Robert Mesropyan](https://www.linkedin.com/in/robert-mesropyan/).

The blog series that explains the pack, and its use cases, is by [Brock Peterson](https://www.linkedin.com/in/brockpetersonbdcvmw/): [part 1](https://www.brockpeterson.com/post/vcommunity-management-pack-for-vcf-operations), [part 2](https://www.brockpeterson.com/post/vcommunity-management-pack-for-vcf-operations-part-2) (Windows checks) and [part 3](https://www.brockpeterson.com/post/vcommunity-management-pack-for-vcf-operations-part-3).

The dashboards, reports, super metrics and the pack's design are by [Iwan Rahabok](https://www.linkedin.com/in/e1ang/). His books are available [here](https://broadcom.box.com/v/OpsYourWorld).

Want to try it first? [Abhijit Timble](https://www.linkedin.com/in/abhijit-timble-75878514/) has installed it on the VMware Hands-on Lab: [test drive this MP](https://labs.hol.vmware.com/HOL/catalog/lab/26848).
