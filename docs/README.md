# Documentation

The documentation follows the [Diátaxis](https://diataxis.fr/) framework: each page has one purpose, and its folder says which.

## How-to guides

Steps to get a task done.

- [Installation](how-to/installation.md): install the PAK file, and activate the metrics the pack needs in the policy.
- [Configuration](how-to/configuration.md): create an Adapter Instance and choose what it collects.
- [Dark Site Installation](how-to/dark-site-installation.md): use a private container registry when the Cloud Proxy has no internet access.
- [Bulk Adapter Instance Importer](../tools/importer/importer.md): create many Adapter Instances from a CSV file.

## Reference

Facts to look up.

- [System Requirements](reference/system-requirements.md): platform versions, registry access, and accounts.
- [Metrics and Properties](reference/metrics-and-properties.md): every property and metric the pack publishes, by object type.

## Explanation

Why the pack exists, how it works, and how each metric is calculated.

- [Introduction](explanation/introduction.md)
- [Why It Matters](explanation/why-it-matters.md)
- [How It Works](explanation/how-it-works.md)

KPIs:

- [Cluster Performance](explanation/kpis/cluster-performance.md)
- [Cluster Risk](explanation/kpis/cluster-risk.md)
- [ESXi Performance](explanation/kpis/esxi-performance.md)
- [VM Performance](explanation/kpis/vm-performance.md)
- [Guest OS Performance](explanation/kpis/guest-os-performance.md)

Other metrics (each page has its Known Limitations):

- [Capacity Utilization](explanation/metrics/capacity-utilization.md)
- [Daily Cluster Check](explanation/metrics/daily-cluster-check.md)
- [Network Speed Degradation](explanation/metrics/network-speed-degradation.md)
- [Operational Availability](explanation/metrics/operational-availability.md)
- [VM Shares](explanation/metrics/vm-shares.md)
- [vSphere World Cluster Metrics](explanation/metrics/vsphere-world-metrics.md)

Dashboards:

- [Extreme Capacity](explanation/dashboards/extreme-capacity.md)

## Design

Plans for future work. Not built.

- [Distributed Switch Health Check](design/distributed-switch-health-check.md)
- [Running Without the Container](design/runtime-without-container.md)

## Where a new page goes

| The page... | Folder |
| :--- | :--- |
| teaches a newcomer by doing, start to end | `tutorials/` (create it with the first tutorial) |
| gives the steps for one task | `how-to/` |
| lists facts: settings, keys, requirements | `reference/` |
| explains a KPI | `explanation/kpis/` |
| explains another metric | `explanation/metrics/` |
| explains a dashboard | `explanation/dashboards/` |
| explains a concept or the architecture | `explanation/` |
| plans work not yet built | `design/` |

Rules:

- One purpose per page. If a page mixes steps and explanation, split it and link the two.
- File and folder names: lowercase, words joined by `-`, no spaces. Do not repeat the folder in the name: `kpis/cluster-risk.md`, not `kpis/cluster-risk-kpi.md`.
- Images go in `images/`. Images of one group go in a subfolder, such as `images/complex-metrics/`.
- Links are relative, such as `../how-to/installation.md`.
- Add every new page to this index.
- When a design is built, move its user-facing content to the right folder, and delete or shorten the design page.
- Check the links before a commit: `python tools/check-docs/check_links.py`. The unit tests run it too.
