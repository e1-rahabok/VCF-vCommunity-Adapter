# Metrics Code

The code that calculates the metrics and KPIs and publishes them to VCF Operations. Read this page before you change or add one. What a KPI means and how its score is calculated is in [How the pack scores a KPI](../concepts/kpi-scoring-models.md#how-the-pack-scores-a-kpi). The metrics as users see them are listed in [Metrics and Properties](../reference/metrics-and-properties.md).

Code: [`Management Pack/app/metrics/`](../../Management%20Pack/app/metrics/)

## Kinds of metric

- **Plain metrics**: one value, read or calculated, and published. For example DRS Score.
- **KPIs**: one 0-100 % score per object, built from many sub-metrics. Most of this folder is KPIs. The scoring is shared, in `kpi_score.py`. Cluster Risk and Cluster Consumption are published as 100 minus their score, so that a higher value is worse.
- **Summaries**: one value over many objects, such as the vSphere World metrics: the worst cluster, or a percentile over the clusters of all vCenters.
- **Availability and counts**: Operational Availability, Network Speed Degradation, the Periodic Cluster Check, and counts such as resource pools, port groups and VMware Tools.
- **Container metrics**: Tier, Business Application and Enterprise performance, published on the objects that VCF Operations uses for Business Applications.

## The six KPIs

All six use the scoring in `kpi_score.py`. Each has its own table of sub-metrics and limits.

| KPI | Object | Sub-metrics | Module |
| :--- | :--- | :--- | :--- |
| Cluster Performance | Cluster | 9 | `cluster/cluster_performance_metrics.py` |
| Cluster Risk | Cluster | 12 | `cluster/cluster_risk_metrics.py` |
| Cluster Consumption | Cluster | 5 | `cluster/cluster_consumption_metrics.py` |
| VM Performance | VM | 9 | `vm/vm_performance_metrics.py` |
| Guest OS Performance | VM | 4 | `vm/guest_os_performance_metrics.py` |
| ESXi Performance | ESXi host | 9 | `host/esxi_performance_metrics.py` |

Each KPI's source limits are shown on its page under [Reference](../reference/metrics/README.md). The Memory Tiering sub-metric of Cluster Consumption has not been confirmed on a live system yet.

## What is in this folder

| File | What it does |
| :--- | :--- |
| `kpi_score.py` | The scoring that every KPI shares: it turns sub-metric values into one 0-100 % score. Also `percentile_90()` and `publish_kpi()`, the last step of every KPI. It makes no API calls. |
| `cluster/cluster_performance_metrics.py` | Cluster Performance KPI. |
| `cluster/cluster_risk_metrics.py` | Cluster Risk KPI, and the Monster VM settings. |
| `cluster/cluster_consumption_metrics.py` | Cluster Consumption KPI. Uses the host stats that Cluster Risk reads. |
| `cluster/drs_metrics.py` | DRS Score, a plain metric. |
| `cluster/periodic_cluster_check.py` | Periodic Cluster Check: Close for Business per cluster, once per period. See [its page](../reference/metrics/periodic-cluster-check.md). |
| `cluster/cluster_availability.py` | Cluster Operational Availability. |
| `cluster/resource_pool_counts.py` | Number of Resource Pools and Cascading Resource Pools. Reads each pool's parents from VCF Operations, not from vCenter. |
| `vm/vm_performance_metrics.py` | VM Performance KPI. Also reads the stats for Guest OS Performance, in the same request. |
| `vm/guest_os_performance_metrics.py` | Guest OS Performance KPI, for VMs with VMware Tools. |
| `vm/vm_guest_os_kpi.py` | VM Guest OS KPI: the average of the VM and Guest OS scores, with a fallback when VMware Tools is missing. |
| `vm/contention_by_vms.py` | The worst-VM and 90th-percentile rows of VM contention, shared by Cluster Performance and ESXi Performance. |
| `host/esxi_performance_metrics.py` | ESXi Performance KPI. |
| `host/host_availability.py` | ESXi Host Operational Availability. |
| `host/host_network_speed.py` | Network Speed Degradation per host, and the degraded-host count. |
| `host/host_bad_network_packets.py` | Bad network packets of one host, as a % of its packets. A row of Cluster Performance and ESXi Performance. |
| `container/business_app_performance.py` | Tier, Business Application and Enterprise performance, on the Container objects. Reads the VM KPIs, the namespaces and the relationships from VCF Operations. Runs as its own job in `adapter.py`. See [Business Application Performance](../reference/metrics/business-application-performance.md). |
| `datacenter/datacenter_network_degradation.py` | Total Network Speed Degradation per Datacenter: the number of its hosts below 100 %. |
| `vcenter/vcenter_availability.py` | Availability of one vCenter's hosts and clusters, read together. Publishes the vCenter's Worst Cluster Operational Availability. |
| `vcenter/vcenter_network_speed.py` | Network speeds of one vCenter's hosts, and their count per Datacenter. |
| `vcenter/vcenter_port_groups.py` | Number of Port Groups on one vCenter: distributed and standard port groups, counted per Datacenter. Reads the vSphere API. |
| `world/cluster_summary_metrics.py` | Over all clusters of all vCenters: worst and Worst 10 Percent Cluster Performance and Cluster Risk, and highest and Highest 10 Percent Cluster Utilization. |
| `world/availability_summary_metrics.py` | Worst Cluster and average ESXi Host Operational Availability, over all vCenters. |
| `world/vsphere_network_degradation.py` | Total Network Speed Degradation, over all vCenters. |
| `world/cluster_close_changes.py` | Cluster Delta Close and Open Counts: the clusters whose Close for Business changed between two windows. |
| `world/port_group_counts.py` | Number of Port Groups on vSphere World: the sum of the vCenters' latest values, with the 15-minute configuration limit. |
| `world/vm_tools_counts.py` | Number of VM without Tools and Number of VMware Tools down on vSphere World, from the VM properties. |

Share per vCPU and Share per MB are published as metrics by `properties/vm/vm_shares.py`. See [Properties](properties.md). The modules outside this folder that these files depend on are described in [Supporting Code](supporting-code.md).

## Read, calculate, publish

Each module keeps three steps apart:

1. **Read.** A function asks VCF Operations for the stats or properties it needs, through `utils/ops_stats.py`.
2. **Calculate.** Pure functions turn the values into the metric. They make no API calls, so the unit tests need no live system.
3. **Publish.** The value is set on the object with `with_metric()`, or through `publish_kpi()`.

This is what lets the unit tests check the formulas with fake data, and lets you read or change a formula without knowing how the data is fetched.

## The parts of a KPI module

Every KPI module has the same parts, in the same order. Follow this layout when you add one.

| Part | What it is |
| :--- | :--- |
| File docstring | What the KPI is, where its limits come from, what is published, and how missing data is handled. |
| `GROUP`, `KPI_NAME`, `KPI_KEY` | The names used in VCF Operations. `KPI_KEY` is `KPI_NAME` plus " Score", because VCF Operations rejects a metric whose key equals the key of its group. |
| Rows and `METRICS` | The table of sub-metrics and limits. |
| `PUBLISHED_METRICS` | The sub-metrics that are published as metrics of their own. |
| Stat keys | The VCF Operations stats the sub-metrics are built from. |
| Sub-metric formulas | One short function per calculated sub-metric, named after it, such as `memory_zip_swap_pct()`. Each returns `None` when it has no data. A KPI built from hosts or VMs calculates each sub-metric per host or VM first, then combines the results, for example by keeping the highest host. |
| Reading stats | The functions that call `utils/ops_stats.py`. |
| Entry point | `collect_..._metrics()`, which the collector calls once per object. It reads the stats, calculates the values and calls `publish_kpi()`. |

Each sub-metric is one `Metric`: its name, unit and five limits, plus an optional last value `True` for "skip when green". Most modules wrap it in a `Row` that also says where the value comes from: a stat as it is, or a formula. From `vm/vm_performance_metrics.py`:

```python
#       name                    unit    best    green   yellow  orange  zero-at  skip-when-green
READY = Row(Metric("CPU Ready",               "%",    0.0,    2.0,    4.0,    8.0,    16.0),
            stat="cpu|20_sec_peak_readyPct")
CPU_RUN = Row(Metric("CPU Run",               "%",    0.0,    95.0,   97.0,   99.0,   100.0,   True),
              stat="cpu|net_run")
ZIP_SWAP = Row(Metric("Memory Zip Swap",      "%",    0.0,    0.25,   0.5,    1.0,    2.0),
               formula=memory_zip_swap_pct)

METRICS = [row.metric for row in ROWS]
```

A higher-is-better row has decreasing limits, such as `Metric("Guest Free Memory", "MB", 1024.0, 512.0, 256.0, 128.0, 0.0)` in `vm/guest_os_performance_metrics.py`. A green limit equal to the best limit marks green as a single value. Both cases are described in [How the pack scores a KPI](../concepts/kpi-scoring-models.md#how-the-pack-scores-a-kpi).

### What is published

The KPI itself is always published. A sub-metric is published only if the object doesn't already have it as a stat, because publishing it again would store the same number twice for every object.

- **Cluster Performance, Cluster Risk, Cluster Consumption and ESXi Performance** publish all their sub-metrics. They are worst, highest or percentile values over the cluster's or host's VMs and hosts, which the object doesn't have.
- **VM Performance** publishes one sub-metric, Memory Zip Swap, because it is calculated. The other eight are VM stats as they are.
- **Guest OS Performance** publishes only the KPI. Its four sub-metrics are VM stats, or a simple conversion of one.

### What happens in one collection cycle

1. `adapter.py` starts the collectors. See [App Folder](app-folder.md).
2. Each collector reads the stats it needs through `utils/ops_stats.py`, in batches of many objects.
3. For each object, the KPI module calculates every sub-metric.
4. `publish_kpi()` rounds the values to two decimals, publishes the sub-metrics in `PUBLISHED_METRICS`, then scores the rounded values and publishes the KPI.

A failure in one KPI doesn't stop the collection. Each entry point catches its own errors and logs a warning.

## How to change a KPI

- **Change a limit:** edit the row. Nothing else.
- **Remove a sub-metric:** delete its row, and the code that supplies its value.
- **Add a sub-metric:** add a row and supply its value. In `vm_performance_metrics.py`, a sub-metric that is a VM stat as it is needs only `stat=` on its row.
- **Change the tiers or the weight:** edit `TIERS` and `weight_for_score()` in `kpi_score.py`. This changes every KPI, so review all six KPI pages.

`define_kpi()` in `definition.py` builds the KPI's definition from the same table, so a limit change needs no change to the adapter definition.

## How to add a KPI

1. Create the module in the folder of its object type, for example `host/host_performance_metrics.py`. Copy the layout of `vm/vm_performance_metrics.py` when each object is scored on its own stats, or `cluster/cluster_performance_metrics.py` when the score is built from child objects.
2. Fill in `GROUP`, `KPI_NAME`, `KPI_KEY`, the rows, `METRICS` and `PUBLISHED_METRICS`.
3. Write the formulas and the entry point.
4. Call the entry point from the collector of that object type. Read the stats once, before the loop over the objects. See [Collectors](collectors.md).
5. Add one line to `definition.py`, `define_kpi(vCommunity, <your module>)`, in the section of that object type. Every unit used in a KPI table must also be in `KPI_UNITS` there.
6. Add the module to `KPI_MODULES` in `tests/test_kpi_score.py`. Its generic tests then check every row of your table.
7. Add a test file with worked examples, and a page under `docs/reference/metrics/`. Add the page to the contents of `docs/README.md`.

## Limitations

- **A new KPI is visible only after the pack is rebuilt and installed,** and the Adapter Instances restarted. See [Tests](tests.md) for the checks before that.
- **Every KPI is one collection cycle behind** the stats it is built from. See [Metrics and Properties](../reference/metrics-and-properties.md).
- **The sub-metric limits come from the source tables** of the vSphere guidance. They are not tuned per environment.
