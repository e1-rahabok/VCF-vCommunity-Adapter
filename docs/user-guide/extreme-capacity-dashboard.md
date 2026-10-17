# Extreme Capacity Dashboard

The **Extreme Capacity** dashboard shows, on one page, how full and how healthy every vSphere cluster is, and drills down from a cluster to its ESXi hosts and VMs.

It is in the `vCommunity` dashboard folder.

Content:

- [`Management Pack/content/dashboards/Extreme Capacity.json`](../../Management%20Pack/content/dashboards/Extreme%20Capacity.json)
- [`Management Pack/content/reports/vSphere Clusters Capacity List.xml`](../../Management%20Pack/content/reports/vSphere%20Clusters%20Capacity%20List.xml)

## Known limitations

> **Read this before using the dashboard.**

- **Requires the pack's metrics.** Most widgets show pack metrics. A widget is blank until the pack has collected them. The Periodic Cluster Check columns stay blank until the first check period ends. See [Periodic Cluster Check](../reference/metrics/periodic-cluster-check.md).
- **Blank, not stale.** A metric whose latest value is more than 10 minutes old is left blank. The Periodic Cluster Check columns are metrics produced once per period, so they show the last window. See [How It Works](../reference/metrics/README.md#no-stale-values).
- **"Worst 10%" equals "worst" with 10 clusters or fewer.** The 10th (or 90th) percentile takes the lowest (or highest) cluster when there are 10 clusters or fewer. See [vSphere World Cluster Metrics](../reference/metrics/vsphere-world-metrics.md).
- **Risk is red when high.** The Risk widgets are red from 75. The Performance widgets are red below 25. See [Cluster Risk KPI](../reference/metrics/cluster-risk.md#bands-red-is-high).
- **Capacity Utilization can be above 100 %.** That means the cluster cannot hold its load if a host fails. See [Capacity Utilization](../reference/metrics/capacity-utilization.md).
- **Capacity Remaining and Time Remaining are not from this pack.** They come from the VCF Operations capacity engine (`OnlineCapacityAnalytics`).
- **The third section has no name.** It is titled "Section 3".

## How to use it

1. Read the **Summary** row: the worst clusters across all vCenters.
2. In **vSphere Clusters**, select a cluster in the list.
3. The widgets on the right show that cluster's Performance, Risk, Utilization and memory pressure.
4. The bottom section lists its ESXi hosts and VMs.
5. Select an ESXi host to list only its VMs.

## Summary

All on the vSphere World object, so they cover every cluster of every vCenter.

| Widget | Metric | Green / yellow / orange / red |
| :--- | :--- | :--- |
| Worst Performance of all Clusters | `vCommunity\|Worst Cluster Performance` | red below 25, orange below 50, yellow below 75 |
| Highest Risk of all Clusters | `vCommunity\|Worst Cluster Risk` | yellow from 25, orange from 50, red from 75 |
| Worst Cluster Operational Availability | `vCommunity\|Availability\|Worst Cluster Operational Availability` | red below 90, orange below 95, yellow below 99 |
| Worst 10% Cluster Performance | `vCommunity\|Bottom 10 Percent Cluster Performance` | as Worst Performance |
| Worst 10% Cluster Risk | `vCommunity\|Bottom 10 Percent Cluster Risk` | as Highest Risk |
| Average ESXi Hosts Operational Availability | `vCommunity\|Availability\|ESXi Hosts Operational Availability` | red below 94, orange below 96, yellow below 98 |

See [vSphere World Cluster Metrics](../reference/metrics/vsphere-world-metrics.md) and [Operational Availability](../reference/metrics/operational-availability.md).

## vSphere Clusters

**Clusters Capacity** (view: vSphere Clusters Capacity List). One row per cluster.

| Column | Key | Source |
| :--- | :--- | :--- |
| Closed? | `vCommunity\|Periodic Cluster Check\|Close for Business` | metric, [Periodic Cluster Check](../reference/metrics/periodic-cluster-check.md). 1 = closed for new workload. |
| Worst Consumption | `vCommunity\|Periodic Cluster Check\|Worst Cluster Consumption` | metric, Periodic Cluster Check. Yellow from 25, orange from 50, red from 75. |
| Worst Performance | `vCommunity\|Periodic Cluster Check\|Worst Cluster Performance` | metric, Periodic Cluster Check. Red below 25, orange below 50, yellow below 75. |
| Worst Risk | `vCommunity\|Periodic Cluster Check\|Worst Cluster Risk` | metric, Periodic Cluster Check. Yellow from 25, orange from 50, red from 75. |
| Capacity Remaining | `OnlineCapacityAnalytics\|capacityRemainingPercentage` | VCF Operations |
| Time Remaining | `OnlineCapacityAnalytics\|timeRemaining` | VCF Operations |

Selecting a cluster fills the widgets below.

| Widget | Content | Thresholds |
| :--- | :--- | :--- |
| Performance | `vCommunity\|Cluster Performance\|Cluster Performance Score` | red below 25, orange below 50, yellow below 75 |
| Risk | `vCommunity\|Cluster Risk\|Cluster Risk Score` | yellow from 25, orange from 50, red from 75 |
| Utilization | `vCommunity\|Capacity\|CPU Utilization` and `Memory Utilization` | CPU: 70 / 80 / 90. Memory: 80 / 85 / 90. |
| High Memory Utilization | Ballooned (`mem\|vmmemctl_average`), Zipped (`mem\|compressed_average`), Swapped (`mem\|swapout_average`) | Ballooned: 5 / 25 / 100 GB. Zipped and Swapped: 1 / 2.5 / 10. |

See [Cluster Performance KPI](../reference/metrics/cluster-performance.md), [Cluster Risk KPI](../reference/metrics/cluster-risk.md), [Cluster Consumption KPI](../reference/metrics/cluster-consumption.md) and [Capacity Utilization](../reference/metrics/capacity-utilization.md).

## Hosts and VMs

| Widget | View | Columns |
| :--- | :--- | :--- |
| ESXi Hosts in the Cluster | ESXi Utilization List | Core and Thread Utilization, Memory Consumed, Utilization, Ballooned, Zipped, Swapped, % VM with Co-Stop, % VM with Ready, Max CPU Co-Stop, Max CPU Ready |
| VMs in the ESXi or Cluster | VM Capacity Consumption | CPU and its Reservation, Memory and its Reservation, Utilization, Consumed, Sum |

The VM list shows the VMs of the selected cluster, or of the selected host.
