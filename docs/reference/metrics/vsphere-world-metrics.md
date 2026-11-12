# vSphere World Cluster Metrics

Six metrics on the **vSphere World** object summarize the [Cluster Performance](cluster-performance.md), [Cluster Risk](cluster-risk.md) and [Cluster Consumption](cluster-consumption.md) scores of every cluster across all vCenters, so you can watch the whole estate in one place.

Worst 10 Percent Cluster Performance replaces the "vSphere Clusters Performance" super metric, which was the average of all clusters.

The vSphere World object also has:

- two Operational Availability metrics, see [Operational Availability](operational-availability.md);
- two counts of clusters whose [Close for Business](periodic-cluster-check.md) changed, see [Close for Business changes](#close-for-business-changes);
- counts of port groups and of VMs with VMware Tools problems, see [Port groups and VMware Tools](#port-groups-and-vmware-tools);
- the Total Network Speed Degradation, see [Network Speed Degradation](network-speed-degradation.md).

Code: [`cluster_summary_metrics.py`](../../../Management%20Pack/app/metrics/world/cluster_summary_metrics.py) for the six cluster metrics, [`cluster_close_changes.py`](../../../Management%20Pack/app/metrics/world/cluster_close_changes.py) for the two counts, and [`port_group_counts.py`](../../../Management%20Pack/app/metrics/world/port_group_counts.py) and [`vm_tools_counts.py`](../../../Management%20Pack/app/metrics/world/vm_tools_counts.py) for the port group and Tools counts.

## Known limitations

> **Read this before you use the metrics.**

- **Stats older than 10 minutes count as no data**, so a cluster without a recent score is left out. See [No stale values](README.md#no-stale-values).
- **A value can be one collection cycle old (5 minutes).** The metrics are built from the cluster scores already stored in VCF Operations, which are those of each cluster's last collection. The clusters of the vCenter being collected get their new scores in the same cycle, after the vSphere World metrics are read.
- **Every Adapter Instance publishes the same values.** There is one vSphere World object, but one Adapter Instance per vCenter. So that the instances do not overwrite each other with the clusters of their own vCenter only, each one reads the clusters of all vCenters and publishes the same values. With many vCenters, the same small calculation runs once per instance.
- **The values can change slightly between two instances' writes.** Two instances that collect a few minutes apart can read different cluster scores.
- **A cluster without a score is left out.** For example, a cluster with no powered-on VMs has no Cluster Performance score.
- **The Close for Business counts wait for every cluster.** They are published only after every cluster has been calculated for the latest Periodic Cluster Check window, so they can come a few cycles after the window ends, like the check itself.
- **Only the latest window is counted.** If collection stops for longer than a window, the windows in between are not counted.
- **The port group and Tools counts can read 0 after a failed read.** See [Port groups and VMware Tools](#port-groups-and-vmware-tools).

## The 6 metrics

All are published on the vSphere World object under `vCommunity`, in %.

| Metric | Calculation |
| :--- | :--- |
| `vCommunity\|Worst 10 Percent Cluster Performance` | The Cluster Performance score that 90 % of the clusters are at or above. |
| `vCommunity\|Worst Cluster Performance` | The lowest Cluster Performance score of any cluster. |
| `vCommunity\|Worst 10 Percent Cluster Risk` | The Cluster Risk that 90 % of the clusters are at or below. |
| `vCommunity\|Worst Cluster Risk` | The highest Cluster Risk of any cluster. |
| `vCommunity\|Highest 10 Percent Cluster Utilization` | The Cluster Consumption score that 10 % of the clusters are at or above. |
| `vCommunity\|Highest Cluster Utilization` | The highest Cluster Consumption score of any cluster. |

Each metric takes the bad end. **Worst 10 Percent** and **Highest 10 Percent** mark the edge of the worst 10 % of the clusters:

- Cluster Performance is higher-is-better, so the bad end is the low end: the 10th percentile and the lowest.
- Cluster Risk and Cluster Consumption are higher-is-worse, so the bad end is the high end: the 90th percentile and the highest. Cluster Utilization here is the Cluster Consumption score, the share of the usable capacity that is consumed.

**10th and 90th percentile.** The clusters are sorted, and the one at position 10 % (or 90 %) of the count, rounded up, is taken. This is the nearest-rank method that the cluster KPIs use. With 20 clusters, the 10th percentile is the 2nd lowest and the 90th percentile the 18th lowest. With 10 clusters or fewer, the 10th percentile is the lowest. With fewer than 10 clusters, the 90th percentile is the highest. In those cases the percentile equals the worst cluster.

## Close for Business changes

Two counts on the vSphere World object, over all clusters of all vCenters. They compare the [Close for Business](periodic-cluster-check.md) value of each cluster in the latest Periodic Cluster Check window with the window before it.

| Metric | Calculation |
| :--- | :--- |
| `vCommunity\|Cluster Delta Close Count` | The number of clusters whose Close for Business changed from 0 (open) to 1 (closed). |
| `vCommunity\|Cluster Delta Open Count` | The number of clusters whose Close for Business changed from 1 (closed) to 0 (open). |

- **Once per window.** The counts are published with the Periodic Cluster Check, once per window after it ends, with the same [settings](periodic-cluster-check.md#settings). Between two windows, the last value stays.
- **A missing value is not a change.** A cluster with no Close for Business in one of the two windows, such as a new cluster, has no earlier state to change from, so it is not counted. This avoids a false count when a cluster is added.
- The values are numbers of clusters.

## Port groups and VMware Tools

Three counts on the vSphere World object, across all vCenters.

| Metric | Calculation |
| :--- | :--- |
| `vCommunity\|Number of Port Groups` | On vSphere World, the sum of the vCenters' counts. On each vCenter, the port groups of its Datacenters. |
| `vCommunity\|Number of VM without Tools` | The VMs whose VMware Tools are not installed. |
| `vCommunity\|Number of VMware Tools down` | The VMs that are powered on, have VMware Tools installed, and whose Tools are not running. |

**Number of Port Groups** is published on two object types, the vCenter and the vSphere World.

- **On each vCenter.** A port group belongs to its Datacenter. Within one Datacenter a name counts once, whether it is a distributed port group or a standard one defined on each host. The same name in two Datacenters of one vCenter counts twice. The count is read from the vSphere API, through each Datacenter's host folder and network folder.
- **Failed read on a vCenter.** Nothing is published for that vCenter in that cycle, so the vCenter object keeps its last value. The 15-minute limit below does not apply to the vCenter object itself.
- **On vSphere World.** The sum of the stored vCenter values. A vCenter's port groups can only be read from that vCenter, so the total is built from what each Adapter Instance published.
- **15 minutes on vSphere World.** The total uses each vCenter's stored value for up to 15 minutes, because a port group count comes from settings and changes rarely. A vCenter whose value is older, or that has never published one, is left out. See [the two limits](README.md#two-limits-10-minutes-and-15-minutes-for-settings-based-metrics).
- **0 on vSphere World.** When no vCenter has a value from the last 15 minutes, or the stats read fails, the total is published as 0.
- **NSX.** Only vCenter is checked, not NSX Manager. An NSX segment that vCenter shows as a distributed port group counts once, as that port group. A segment that vCenter does not show, such as one not realized on a distributed switch, is not counted.
- A vCenter without an Adapter Instance of this pack has no value and is left out.

**VMware Tools.** The two Tools counts are read from the VM properties that the vCenter adapter stores. Their possible values, as VCF Operations shows them:

| Property | Possible values |
| :--- | :--- |
| `Summary\|Guest Operating System\|Tools Running Status` | Guest Tools Running, Guest Tools Not Running |
| `Summary\|Guest Operating System\|Tools Version Status` | Guest Tools Current, Guest Tools Supported Old, Guest Tools Too Old, Guest Tools Unmanaged, Guest Tools Not Installed |

- **Without Tools** means the Tools status is *Not Installed*. It counts whatever the power state, because the Tools are not installed.
- **Tools down** needs three things: the VM is powered on, its Tools are installed, and its Tools are not running. A powered-off VM never counts, because a property keeps its last value, so a powered-off VM still shows the Tools status it had when it was last on.
- A VM with no stored Tools value, such as a template, is left out of both counts.
- If the properties read fails, both counts are published as 0 for that cycle. The adapter log has a warning.

## Example

Three clusters have Cluster Performance scores of 86.35, 98 and 50. Worst Cluster Performance is 50. With fewer than 10 clusters, the 10th percentile is also the lowest, 50.

The tests in [`Management Pack/tests/test_cluster_summary_metrics.py`](../../../Management%20Pack/tests/test_cluster_summary_metrics.py) check the same example.
