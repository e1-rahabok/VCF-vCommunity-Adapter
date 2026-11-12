# vSphere Cluster Capacity 2.0 Dashboard

The **vSphere Cluster Capacity 2.0** dashboard shows how full and how healthy each vSphere cluster is. It shows the three cluster KPIs (Performance, Risk and Consumption), the sub-metrics behind them, and the configuration of the selected cluster, and it drills down from a cluster to its ESXi hosts and VMs. It is meant for a weekly review and complements the Overall Daily Check dashboard.

The dashboard is in the `vCommunity` dashboard folder. Its file is [`Management Pack/content/dashboards/vSphere Cluster Capacity 2.0.json`](../../Management%20Pack/content/dashboards/vSphere%20Cluster%20Capacity%202.0.json).

## Known limitations

- **Most widgets need the pack's metrics.** A widget stays blank until the pack has collected them. The Periodic Cluster Check columns stay blank until the first check period ends. See [Periodic Cluster Check](../reference/metrics/periodic-cluster-check.md).
- **Old values are left blank.** A metric whose latest value is more than 10 minutes old is not shown. The Periodic Cluster Check columns are published once per period, so they show the last completed window. See [No stale values](../reference/metrics/README.md#no-stale-values).
- **Some tiles have no color bands.** In the Risk and Contention scoreboards, many tiles have all three bounds set to 0, so their color does not mean anything. Read the value. The three KPI gauges have bands.
- **Capacity Remaining and Time Remaining come from VCF Operations**, from its capacity engine (`OnlineCapacityAnalytics`), not from this pack.
- **The gauges point in different directions.** The Risk and Consumption gauges are red from 75. The Contention gauge, which shows the Cluster Performance score, is red below 25. See [Cluster Risk](../reference/metrics/cluster-risk.md#bands-red-is-high).

## How to use it

1. In **vSphere Clusters**, select a cluster in the **Clusters Capacity** list.
2. The gauges show that cluster's **Contention**, **Risk** and **Consumption**.
3. The scoreboards under the gauges show the sub-metrics behind each KPI.
4. **Details of Selected Cluster** lists the cluster's ESXi hosts and VMs, and its configuration.
5. Select an ESXi host to list only its VMs.

## Clusters being opened

Two charts at the top, both titled **Clusters being opened**, show `vCommunity|Cluster Delta Open Count` over time: the number of clusters whose Close for Business went from 1 (closed) to 0 (open) since the previous Periodic Cluster Check window. See [Close for Business changes](../reference/metrics/vsphere-world-metrics.md#close-for-business-changes). No widget on this dashboard shows the matching Close Count.

## vSphere Clusters

**Clusters Capacity** has one row per cluster:

| Column | Key | Source |
| :--- | :--- | :--- |
| Closed? | `vCommunity\|Periodic Cluster Check\|Close for Business` | Metric, [Periodic Cluster Check](../reference/metrics/periodic-cluster-check.md). 1 means closed for new workloads. |
| Worst Consumption | `vCommunity\|Periodic Cluster Check\|Worst Cluster Consumption` | Metric, Periodic Cluster Check |
| Worst Performance | `vCommunity\|Periodic Cluster Check\|Worst Cluster Performance` | Metric, Periodic Cluster Check |
| Worst Risk | `vCommunity\|Periodic Cluster Check\|Worst Cluster Risk` | Metric, Periodic Cluster Check |
| Capacity Remaining | `OnlineCapacityAnalytics\|capacityRemainingPercentage` | VCF Operations |

The list is scoped to the vSphere World object, so it covers every cluster in every vCenter.

## Cluster KPIs (gauges)

The gauges show the selected cluster. Each is a score from 0 to 100.

| Gauge | Metric | Bands |
| :--- | :--- | :--- |
| Contention (%) | `vCommunity\|Cluster Performance\|Cluster Performance Score` | Red below 25, orange below 50, yellow below 75 |
| Risk (%) | `vCommunity\|Cluster Risk\|Cluster Risk Score` | Yellow from 25, orange from 50, red from 75 |
| Consumption (%) | `vCommunity\|Cluster Consumption\|Cluster Consumption Score` | Yellow from 25, orange from 50, red from 75 |

See [Cluster Performance](../reference/metrics/cluster-performance.md), [Cluster Risk](../reference/metrics/cluster-risk.md) and [Cluster Consumption](../reference/metrics/cluster-consumption.md).

## Sub-metric scoreboards

Each scoreboard lists the sub-metrics behind one KPI. Each tile is colored against its own bounds in the dashboard. For all of them, a high value is bad.

| Scoreboard | Sub-metrics |
| :--- | :--- |
| **Consumption** | Cluster-wide ESXi CPU Thread Utilization, Cluster-wide ESXi Memory Consumed, Cluster-wide ESXi Memory Ballooned, Cluster-wide ESXi Memory Zip Swap |
| **Contention** | Worst VM Memory Latency, Worst VM Disk Latency, Worst VM CPU Ready, Worst VM CPU Co-Stop, Highest ESXi Bad Network Packets |
| **Risk** | Highest ESXi CPU Thread Utilization, Worst ESXi CPU Imbalance, Highest ESXi Memory Consumed, Worst ESXi Memory Ballooned, Worst ESXi Memory Zip Swap, Highest ESXi CPU Overcommit Ratio, Highest ESXi Memory Reservation, Highest ESXi CPU Reservation, Highest ESXi Memory Overcommit Ratio, Highest CPU Monster VM to Host Ratio, Highest Memory Monster VM to Host Ratio |

The sub-metrics are defined on the KPI pages: [Cluster Performance](../reference/metrics/cluster-performance.md), [Cluster Risk](../reference/metrics/cluster-risk.md) and [Cluster Consumption](../reference/metrics/cluster-consumption.md).

## Context

The **Context** scoreboard next to the gauges shows the selected cluster's running VMs, usable cores, running VM vCPUs, usable memory and memory utilization.

## Details of Selected Cluster

| Widget | View or type | Content |
| :--- | :--- | :--- |
| ESXi Hosts in the Cluster | View: ESXi Utilization List | Core and thread utilization, memory consumed and utilization, ballooned, compressed and swapped memory, the percentage of VMs with CPU Co-Stop and CPU Ready, and the highest CPU Co-Stop and CPU Ready |
| CPU Utilization (%), Memory Utilization (GB), High Memory Utilization | Views and a scoreboard | Cluster CPU and memory utilization, and high memory pressure (ballooned, compressed, swapped) |
| VMs in the ESXi or Cluster | View: VM Capacity Consumption | vCPUs, CPU and memory reservations, memory demand and consumed memory |
| Relevant Configuration (HA, DPM and location) | Scoreboard | HA enabled and admission control, the HA admission control policy, DPM enabled, datacenter, tag and folder |
| Relevant Configuration (hardware) | Scoreboard | Hardware model and vendor, hyper-threading, CPU speed per core, number of CPU cores, usable memory |

The VM list shows the VMs of the selected cluster, or of the selected host.

---

See [Included Content](included-content.md) for the other dashboards in the pack.
