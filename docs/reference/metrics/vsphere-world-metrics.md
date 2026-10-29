# vSphere World Cluster Metrics

Six metrics on the **vSphere World** object summarise the [Cluster Performance](cluster-performance.md), [Cluster Risk](cluster-risk.md) and [Cluster Consumption](cluster-consumption.md) scores of every cluster, across all vCenters. Use them to watch the whole estate in one place.

Bottom 10 Percent Cluster Performance replaces the "vSphere Clusters Performance" super metric, which was the average of all clusters.

The vSphere World object also has two Operational Availability metrics. See [Operational Availability](operational-availability.md).

Two more count how many clusters changed their [Close for Business](periodic-cluster-check.md), see [Close for Business changes](#close-for-business-changes).

Code: [`Management Pack/app/metrics/world/cluster_summary_metrics.py`](../../../Management%20Pack/app/metrics/world/cluster_summary_metrics.py), and [`cluster_close_changes.py`](../../../Management%20Pack/app/metrics/world/cluster_close_changes.py) for the two counts

## Known limitations

> **Read this before using the metrics.**

- **No stale values.** A stat whose latest value is more than 10 minutes old is treated as no data, so the metric is left blank rather than showing a value that no longer reflects reality. Properties keep their last known value. See [How It Works](../../reference/metrics/README.md#no-stale-values).
- **A value can be up to one collection cycle old (5 minutes).** The metrics are built from the cluster scores already stored in VCF Operations. The score of a cluster is the one of its last collection. The clusters of the vCenter being collected get their new score in the same cycle, after the vSphere World metrics are read.
- **Every account calculates the same values.** There is one vSphere World object, but one account of this pack per vCenter. So that the accounts do not overwrite each other with the clusters of their own vCenter only, every account reads the clusters of all vCenters and publishes the same values. With many vCenters, this is the same small calculation done once per account.
- **The values can move slightly between two accounts' writes.** Two accounts that collect a few minutes apart can read different cluster scores, so the vSphere World values can change between their two writes.
- **A cluster without a score is left out.** For example, a cluster with no powered-on VMs has no Cluster Performance score.
- **The Close for Business counts wait for every cluster.** They are not published until every cluster is calculated for the latest Periodic Cluster Check window, so they can come a few cycles after the window ends, like the check itself.
- **Only the latest window is counted.** If the collection stops for longer than a window, the windows in between are not counted.

## The 6 metrics

All are published on the vSphere World object under `vCommunity`, in %.

| Metric | Calculation |
| :--- | :--- |
| `vCommunity\|Bottom 10 Percent Cluster Performance` | The Cluster Performance score that 90 % of the clusters are at or above. |
| `vCommunity\|Worst Cluster Performance` | The lowest Cluster Performance score of any cluster. |
| `vCommunity\|Bottom 10 Percent Cluster Risk` | The Cluster Risk that 90 % of the clusters are at or below. |
| `vCommunity\|Worst Cluster Risk` | The highest Cluster Risk of any cluster. |
| `vCommunity\|Top 10 Percent Cluster Utilization` | The Cluster Consumption score that 10 % of the clusters are at or above. |
| `vCommunity\|Highest Cluster Utilization` | The highest Cluster Consumption score of any cluster. |

Each metric takes the bad end. **Bottom 10 Percent** and **Top 10 Percent** are the boundary of the worst 10 % of the clusters, whichever direction is worse, so the name means the same for each KPI:

- Cluster Performance is "higher is better", so the bad end is the low end: the 10th percentile and the lowest.
- Cluster Risk and Cluster Consumption are "higher is worse" (100 = maximum), so the bad end is the high end: the 90th percentile and the highest. Cluster Utilization is the Cluster Consumption score: the share of the usable capacity consumed.

**10th and 90th percentile.** The clusters are sorted, and the one at position 10 % (or 90 %) of the count, rounded up, is taken (nearest rank, the same method as the cluster KPIs). With 20 clusters that is the 2nd lowest (or the 18th lowest). With 10 clusters or fewer it is the lowest (or the highest), the same as the worst cluster.

## Close for Business changes

Two counts on the vSphere World object, over all clusters of all vCenters. They compare the [Close for Business](periodic-cluster-check.md) of each cluster in the latest Periodic Cluster Check window with the window before it.

| Metric | Calculation |
| :--- | :--- |
| `vCommunity\|Cluster Delta Close Count` | The number of clusters whose Close for Business changed from 0 (open) to 1 (closed). |
| `vCommunity\|Cluster Delta Open Count` | The number of clusters whose Close for Business changed from 1 (closed) to 0 (open). |

- **Once per window, not every 5 minutes.** The counts are published with the Periodic Cluster Check: once per window, after its window ends, with the same [settings](periodic-cluster-check.md#settings). Between two windows, the last value stays.
- **A blank value is not counted.** A cluster with no Close for Business in one of the two windows, such as a new cluster, has no earlier state to change from, so it is not counted as a change. This avoids a false count when a cluster is added.
- **A count, not a percentage.** The values are numbers of clusters.

## Port groups and VMware Tools

Three counts on the vSphere World object, over all vCenters.

| Metric | Calculation |
| :--- | :--- |
| `vCommunity\|Number of Port Groups` | On vSphere World, the sum of the vCenters' counts. On each vCenter, the port groups of its Datacenters. |
| `vCommunity\|Number of VM without Tools` | The VMs whose VMware Tools are not installed. |
| `vCommunity\|Number of VMware Tools down` | The VMs that are powered on, have VMware Tools installed, and whose Tools are not running. |

**Number of Port Groups.** The same metric is published on two object types, the vCenter and the vSphere World.

- **On each vCenter.** A port group's namespace is its Datacenter. Within one Datacenter, a name counts once, whether it is a distributed port group or a standard one (defined on each host). The same name in two Datacenters of one vCenter counts twice. The count is read from the vSphere API, through each Datacenter's host folder and network folder.
- **On vSphere World.** The sum of the vCenters' values. It is read from the stored vCenter values, not computed directly, because the port groups of a vCenter can only be read from that vCenter.
- **Staleness: 15 minutes, not 10.** The vSphere World total uses each vCenter's last value for up to 15 minutes. This is the one exception to the 10-minute rule, because a port group count is based on settings and changes rarely. A vCenter whose value is older than 15 minutes is left out. See [the two limits](README.md#two-limits-10-minutes-and-15-minutes-for-settings-based-metrics).
- **Failed read.** Nothing is published for that vCenter in that cycle, so its last value stays, and no false zero is stored.
- **NSX.** Only vCenter is checked, not NSX Manager. An NSX segment that vCenter shows as a distributed port group is counted once, as that port group. A segment that vCenter does not show, such as one that is not realised on a distributed switch, is not counted.
- A vCenter without an account of this pack has no value, and is left out.

**VMware Tools.** Read from the VM properties that the vCenter adapter stores. Their possible values, as shown in VCF Operations:

| Property | Possible values |
| :--- | :--- |
| `Summary\|Guest Operating System\|Tools Running Status` | Guest Tools Running, Guest Tools Not Running |
| `Summary\|Guest Operating System\|Tools Version Status` | Guest Tools Current, Guest Tools Supported Old, Guest Tools Too Old, Guest Tools Unmanaged, Guest Tools Not Installed |

- **Without Tools** is the VM's Tools status *Not Installed*. It is counted whatever the power state, because the Tools are not installed.
- **Tools down** needs three things: the VM is powered on, its Tools are installed, and its Tools are not running. A powered-off VM is never counted: a property keeps its last value, so a powered-off VM keeps the Tools status it had when it was last on.
- A VM with no stored Tools value, such as a template, is left out of both counts.

## Example

Three clusters with Cluster Performance scores 86.35, 98 and 50. Worst Cluster Performance is 50. With fewer than 10 clusters, the 10th percentile is also the lowest: 50.

The same example is checked by the tests in [`Management Pack/tests/test_cluster_summary_metrics.py`](../../../Management%20Pack/tests/test_cluster_summary_metrics.py).
