# vSphere Cluster Capacity 2.0 Dashboard

The **vSphere Cluster Capacity 2.0** dashboard shows, on one page, how full and how healthy each vSphere cluster is. It shows the three cluster KPIs (Performance, Risk and Consumption), the sub-metrics behind them, and the configuration of the selected cluster. From a cluster it drills down to its ESXi hosts and VMs.

Content:

- [`Management Pack/content/dashboards/vSphere Cluster Capacity 2.0.json`](../../Management%20Pack/content/dashboards/vSphere%20Cluster%20Capacity%202.0.json)

It is in the `vCommunity` dashboard folder.

## Known limitations

> **Read this before using the dashboard.**

- **Requires the pack's metrics.** Most widgets show pack metrics. A widget is blank until the pack has collected them. The Periodic Cluster Check columns stay blank until the first check period ends. See [Periodic Cluster Check](../reference/metrics/periodic-cluster-check.md).
- **Blank, not stale.** A metric whose latest value is more than 10 minutes old is left blank. The Periodic Cluster Check columns are metrics produced once per period, so they show the last window. See [How It Works](../reference/metrics/README.md#no-stale-values).
- **Some tiles have no colour bands.** In the Risk and Contention scoreboards, many tiles have all three bounds set to 0 in the dashboard. Their colour does not show a level, so read the value. The three KPI gauges (Contention, Risk and Consumption) do have bands.
- **Capacity Remaining and Time Remaining are not from this pack.** They come from the VCF Operations capacity engine (`OnlineCapacityAnalytics`).
- **Risk is red when high.** The Risk and Consumption gauges are red from 75. The Contention gauge is red below 25. See [Cluster Risk KPI](../reference/metrics/cluster-risk.md#bands-red-is-high).

## How to use it

1. In **vSphere Clusters**, select a cluster in the **Clusters Capacity** list.
2. The gauges show that cluster's **Contention**, **Risk** and **Consumption**.
3. The scoreboards under the gauges show the sub-metrics behind each KPI.
4. **Details of Selected Cluster** lists the cluster's ESXi hosts and VMs, and its configuration.
5. Select an ESXi host to list only its VMs.

## vSphere Clusters

**Clusters Capacity**. One row per cluster.

| Column | Key | Source |
| :--- | :--- | :--- |
| Closed? | `vCommunity\|Periodic Cluster Check\|Close for Business` | metric, [Periodic Cluster Check](../reference/metrics/periodic-cluster-check.md). 1 = closed for new workload. |
| Worst Consumption | `vCommunity\|Periodic Cluster Check\|Worst Cluster Consumption` | metric, Periodic Cluster Check. |
| Worst Performance | `vCommunity\|Periodic Cluster Check\|Worst Cluster Performance` | metric, Periodic Cluster Check. |
| Worst Risk | `vCommunity\|Periodic Cluster Check\|Worst Cluster Risk` | metric, Periodic Cluster Check. |
| Capacity Remaining | `OnlineCapacityAnalytics\|capacityRemainingPercentage` | VCF Operations |

The list is filtered to the vSphere World object, so it covers every cluster of every vCenter.

## Cluster KPIs (gauges)

These gauges show the selected cluster. Each is a 0 to 100 score.

| Gauge | Metric | Green / yellow / orange / red |
| :--- | :--- | :--- |
| Contention (%) | `vCommunity\|Cluster Performance\|Cluster Performance Score` | red below 25, orange below 50, yellow below 75 |
| Risk (%) | `vCommunity\|Cluster Risk\|Cluster Risk Score` | yellow from 25, orange from 50, red from 75 |
| Consumption (%) | `vCommunity\|Cluster Consumption\|Cluster Consumption Score` | yellow from 25, orange from 50, red from 75 |

See [Cluster Performance KPI](../reference/metrics/cluster-performance.md), [Cluster Risk KPI](../reference/metrics/cluster-risk.md) and [Cluster Consumption KPI](../reference/metrics/cluster-consumption.md).

## Sub-metric scoreboards

Each scoreboard lists the sub-metrics behind one KPI. A tile is coloured against its own bounds in the dashboard. High is bad for all of them.

| Scoreboard | Sub-metrics |
| :--- | :--- |
| **Consumption** | Cluster-wide ESXi CPU Thread Utilization, Cluster-wide ESXi Memory Consumed, Cluster-wide ESXi Memory Ballooned, Cluster-wide ESXi Memory Zip Swap |
| **Contention** | Worst VM Memory Latency, Worst VM Disk Latency, Worst VM CPU Ready, Worst VM CPU Co-Stop, Highest ESXi Bad Network Packets |
| **Risk** | Highest ESXi CPU Thread Utilization, Worst ESXi CPU Imbalance, Highest ESXi Memory Consumed, Worst ESXi Memory Ballooned, Worst ESXi Memory Zip Swap, Highest ESXi CPU Overcommit Ratio, Highest ESXi Memory Reservation, Highest ESXi CPU Reservation, Highest ESXi Memory Overcommit Ratio, Highest CPU Monster VM to Host Ratio, Highest Memory Monster VM to Host Ratio |

The sub-metrics are defined in the KPI pages: [Cluster Performance](../reference/metrics/cluster-performance.md), [Cluster Risk](../reference/metrics/cluster-risk.md) and [Cluster Consumption](../reference/metrics/cluster-consumption.md).

## Context

The **Context** scoreboard, next to the gauges, shows the selected cluster's running VMs, usable cores, running VM vCPUs, usable memory and memory utilisation.

## Details of Selected Cluster

| Widget | View | Content |
| :--- | :--- | :--- |
| ESXi Hosts in the Cluster | ESXi Utilization List | Core and thread utilisation, memory consumed and utilisation, ballooned, zipped and swapped memory, % of VMs with CPU Co-Stop and CPU Ready, maximum CPU Co-Stop and CPU Ready |
| CPU Utilization (%), Memory Utilization (GB), High Memory Utilization | Views and scoreboard | Cluster CPU and memory utilisation, and the high memory pressure (ballooned, zipped, swapped) |
| VMs in the ESXi or Cluster | VM Capacity Consumption | Number of vCPUs, CPU and memory reservations, memory demand and consumed memory |
| Relevant Configuration (HA, DPM and location) | Scoreboard | HA enabled and admission control, the HA admission control policy, DPM enabled, datacenter, tag and folder |
| Relevant Configuration (hardware) | Scoreboard | Hardware model and vendor, hyper-threading, CPU speed per core, number of CPU cores, usable memory |

The VM list shows the VMs of the selected cluster, or of the selected host.
