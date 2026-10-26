# Metrics Code

The code that calculates the metrics and KPIs, and publishes them to VCF Operations. This page is for changing or adding one. For what a KPI means and how its score is calculated, see [How the pack scores a KPI](../concepts/kpi-scoring-models.md#how-the-pack-scores-a-kpi). For the metrics users see, see [Metrics and Properties](../reference/metrics-and-properties.md).

Code: [`Management Pack/app/metrics/`](../../Management%20Pack/app/metrics/)

## The kinds of metric

- **Plain metrics.** One value, read or calculated and published. Example: DRS Score.
- **KPIs.** One 0-100 % score per object, built from many sub-metrics. Most of this folder is KPIs. The scoring is shared, in `kpi_score.py`. Cluster Risk and Cluster Consumption are published as 100 minus their score, so that higher means worse.
- **Summaries.** One value over many objects, such as the vSphere World metrics: the worst cluster, or a percentile of the clusters of all vCenters.
- **Availability and counts.** Operational Availability, Network Speed Degradation and the Periodic Cluster Check.

## The six KPIs

All six use the same scoring, in `kpi_score.py`. Each has its own table of sub-metrics and limits.

| KPI | Object | Sub-metrics | Module |
| :--- | :--- | :--- | :--- |
| Cluster Performance | Cluster | 9 | `cluster/cluster_performance_metrics.py` |
| Cluster Risk | Cluster | 12 | `cluster/cluster_risk_metrics.py` |
| Cluster Consumption | Cluster | 5 | `cluster/cluster_consumption_metrics.py` |
| VM Performance | VM | 9 | `vm/vm_performance_metrics.py` |
| Guest OS Performance | VM | 4 | `vm/guest_os_performance_metrics.py` |
| ESXi Performance | ESXi host | 9 | `host/esxi_performance_metrics.py` |

Each KPI's source limits are shown in its page under [Reference](../reference/metrics/README.md). Cluster Consumption's Memory Tiering sub-metric is not yet confirmed on a live system.

## What is in this folder

| File | What it does |
| :--- | :--- |
| `kpi_score.py` | The scoring shared by every KPI: it turns sub-metric values into one 0-100 % score. Also `publish_kpi()`, the last step of every KPI. It makes no API calls. |
| `cluster/cluster_performance_metrics.py` | Cluster Performance KPI. |
| `cluster/cluster_risk_metrics.py` | Cluster Risk KPI. |
| `cluster/cluster_consumption_metrics.py` | Cluster Consumption KPI. Uses the host stats Cluster Risk reads. |
| `cluster/drs_metrics.py` | DRS Score. A plain metric. |
| `cluster/periodic_cluster_check.py` | Periodic Cluster Check: once per period, Close for Business per cluster. See [its page](../reference/metrics/periodic-cluster-check.md). |
| `cluster/cluster_availability.py` | Cluster Operational Availability. |
| `vm/vm_performance_metrics.py` | VM Performance KPI. Also reads the stats of Guest OS Performance. |
| `vm/guest_os_performance_metrics.py` | Guest OS Performance KPI, for VMs with VMware Tools. |
| `vm/vm_guest_os_kpi.py` | VM Guest OS KPI: the average of the guest OS scores, with a fallback when VMware Tools is missing. |
| `vm/contention_by_vms.py` | The worst-VM and 90th-percentile rows of VM contention, shared by Cluster Performance and ESXi Performance. |
| `host/esxi_performance_metrics.py` | ESXi Performance KPI. |
| `host/host_availability.py` | ESXi Host Operational Availability. |
| `host/host_network_speed.py` | Network Speed Degradation per host, and the degraded-host count. |
| `host/host_bad_network_packets.py` | Bad network packets of one host, as a % of its packets. A row of Cluster Performance and ESXi Performance. |
| `datacenter/datacenter_network_degradation.py` | Total Network Speed Degradation per Datacenter: the number of its hosts below 100 %. |
| `vcenter/vcenter_availability.py` | Availability of one vCenter's hosts and clusters, read together. Publishes its Worst Cluster Operational Availability. |
| `vcenter/vcenter_network_speed.py` | Network speeds of one vCenter's hosts, and their count per Datacenter. |
| `world/cluster_summary_metrics.py` | Bottom 10 Percent and worst Cluster Performance and Cluster Risk, over all clusters of all vCenters. |
| `world/availability_summary_metrics.py` | Worst Cluster and average ESXi Host Operational Availability, over all vCenters. |
| `world/vsphere_network_degradation.py` | Total Network Speed Degradation, over all vCenters. |
| `world/cluster_close_changes.py` | Cluster Delta Close and Open Count: clusters whose Close for Business changed between two windows. |

The files outside this folder that these modules depend on are in [Supporting Code](supporting-code.md).

## The design: read, calculate, publish

Each module separates three steps:

1. **Read.** A function asks VCF Operations for the stats or properties it needs, through `utils/ops_stats.py`.
2. **Calculate.** Pure functions turn those values into the metric. They make no API call, so the tests need no live system.
3. **Publish.** The value is set on the object, with `with_metric()` or through `publish_kpi()`.

This is why the unit tests can check the formulas with fake data. It also means a formula can be read and changed without knowing how the data is fetched.

## The parts of a KPI module

Every KPI module has the same parts, in the same order. Keep to this when you add one.

| Part | What it is |
| :--- | :--- |
| File docstring | What the KPI is, where its limits come from, what is published, how missing data is handled. |
| `GROUP`, `KPI_NAME`, `KPI_KEY` | The names used in VCF Operations. `KPI_KEY` is `KPI_NAME` plus " Score", because VCF Operations rejects a metric whose key equals the key of its group. |
| `METRICS` | The table of sub-metrics and limits. |
| `PUBLISHED_METRICS` | The sub-metrics that are published. |
| Stat keys | The VCF Operations stats the sub-metrics are built from. |
| Sub-metric formulas | One short function per calculated sub-metric, named after it, such as `memory_zip_swap_pct()`. Each returns `None` when it has no data. A KPI built from hosts or VMs calculates each sub-metric per host or VM first, then combines them, such as keeping the highest host. |
| Reading stats | The functions that call `utils/ops_stats.py`. |
| Entry point | `collect_..._metrics()`, called by the collector once per object. It reads the stats, calculates the values and calls `publish_kpi()`. |

The limits are one table per KPI, in `METRICS`. One row is one sub-metric: its name, its unit, and five limits:

```python
METRICS = [
    #       name                 unit   best    green  yellow  orange  zero-at
    Metric("CPU Ready",          "%",   0.0,    2.0,   4.0,    8.0,    16.0),
    Metric("CPU Run",            "%",   60.0,   80.0,  90.0,   95.0,   100.0),
    Metric("Guest Free Memory",  "MB",  1024.0, 512.0, 256.0,  128.0,  0.0),
]
```

A green limit equal to best marks a single green value. A row with the last value `True` is skipped when green. Both are described in [How the pack scores a KPI](../concepts/kpi-scoring-models.md#how-the-pack-scores-a-kpi).

### What is published

The KPI itself is always published. A sub-metric is published only if the object does not already have it as a stat. Publishing a stat the object already has would store every number twice, for every object.

- **Cluster Performance** publishes all 9 sub-metrics. They are worst values and 90th percentiles over the cluster's VMs and hosts, so the cluster does not have them.
- **VM Performance** publishes one sub-metric, Memory Zip Swap, because it is calculated. The other 8 are read from stats the VM already has.
- **Guest OS Performance** publishes only the KPI. Its 4 sub-metrics are stats the VM already has, or a simple conversion of one.

### What happens in one collection cycle

1. `adapter.py` starts one collector per object type. See [App Folder](app-folder.md).
2. The collector reads the stats it needs in one request for many objects, through `utils/ops_stats.py`.
3. For each object, the KPI module calculates every sub-metric.
4. `publish_kpi()` rounds the values to two decimals, publishes the sub-metrics in `PUBLISHED_METRICS`, then scores the rounded values and publishes the KPI.

A failure in one KPI never stops the collection. Each entry point catches its own errors and writes a warning to the adapter log.

## How to change a KPI

- **Change a limit:** edit the row in `METRICS`. Nothing else.
- **Remove a sub-metric:** delete its row, and the line that supplies its value.
- **Add a sub-metric:** add a row, and supply its value. In `vm_performance_metrics.py` that is one line in `SOURCE_STATS` when the value is a VM stat as it is.
- **Change tiers or the weight:** edit `TIERS` and `weight_for_score()` in `kpi_score.py`. This changes every KPI, so it needs a review of all six KPI pages.

The adapter definition reads the same tables, so there is nothing to update in `adapter.py` for a limit change.

## How to add a KPI

1. Create the module under the folder of its object type, for example `host/host_performance_metrics.py`. Copy the structure of `vm/vm_performance_metrics.py` when every object is scored on its own stats. Copy `cluster/cluster_performance_metrics.py` when the score is built from child objects.
2. Fill in `GROUP`, `KPI_NAME`, `KPI_KEY`, `METRICS` and `PUBLISHED_METRICS`.
3. Write the formulas and the entry point.
4. Call the entry point from the collector of that object type. Read the stats once, before the loop over the objects. See [Collectors](collectors.md).
5. Add one line to `adapter.py`: `define_kpi(vCommunity, <your module>)`, in the section of that object type. A unit used in a KPI table must also be listed in `KPI_UNITS` there.
6. Add the module to `KPI_MODULES` in `tests/test_kpi_score.py`. Two tests then check every row of your table.
7. Add a test file with worked examples, and a page under `docs/reference/metrics/`. Add it to the contents of `docs/README.md`.

## Limitations

- **A new KPI is not visible until the pack is rebuilt and installed,** and the Adapter Instances restarted. See [Tests](tests.md) for the checks before that.
- **Every KPI is one collection cycle behind** the stats it is built from. See [Metrics and Properties](../reference/metrics-and-properties.md).
- **Sub-metric limits come from the source tables** of the vSphere guidance, and are not tuned per environment.
