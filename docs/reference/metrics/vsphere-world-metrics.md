# vSphere World Cluster Metrics

Four metrics on the **vSphere World** object summarise the [Cluster Performance](cluster-performance.md) and [Cluster Risk](cluster-risk.md) scores of every cluster, across all vCenters. Use them to watch the whole estate in one place.

10th Percentile Cluster Performance replaces the "vSphere Clusters Performance" super metric, which was the average of all clusters.

The vSphere World object also has two Operational Availability metrics. See [Operational Availability](operational-availability.md).

Code: [`Management Pack/app/metrics/world/cluster_summary_metrics.py`](../../../Management%20Pack/app/metrics/world/cluster_summary_metrics.py)

## Known limitations

> **Read this before using the metrics.**

- **No stale values.** A stat whose latest value is more than 10 minutes old is treated as no data, so the metric is left blank rather than showing a value that no longer reflects reality. Properties keep their last known value. See [How It Works](../../reference/metrics/README.md#no-stale-values).
- **A value can be up to one collection cycle old (5 minutes).** The metrics are built from the cluster scores already stored in VCF Operations. The score of a cluster is the one of its last collection. The clusters of the vCenter being collected get their new score in the same cycle, after the vSphere World metrics are read.
- **Every account calculates the same values.** There is one vSphere World object, but one account of this pack per vCenter. So that the accounts do not overwrite each other with the clusters of their own vCenter only, every account reads the clusters of all vCenters and publishes the same values. With many vCenters, this is the same small calculation done once per account.
- **The values can move slightly between two accounts' writes.** Two accounts that collect a few minutes apart can read different cluster scores, so the vSphere World values can change between their two writes.
- **A cluster without a score is left out.** For example, a cluster with no powered-on VMs has no Cluster Performance score.

## The 4 metrics

All are published on the vSphere World object under `vCommunity`, in %.

| Metric | Calculation |
| :--- | :--- |
| `vCommunity\|10th Percentile Cluster Performance` | The Cluster Performance score that 90 % of the clusters are at or above. |
| `vCommunity\|Worst Cluster Performance` | The lowest Cluster Performance score of any cluster. |
| `vCommunity\|90th Percentile Cluster Risk` | The Cluster Risk that 90 % of the clusters are at or below. |
| `vCommunity\|Worst Cluster Risk` | The highest Cluster Risk of any cluster. |

Each metric takes the bad end:

- Cluster Performance is "higher is better", so the bad end is the low end: the 10th percentile and the lowest.
- Cluster Risk is "higher is worse" (100 = maximum risk), so the bad end is the high end: the 90th percentile and the highest. "10th Percentile Cluster Risk" was replaced by "90th Percentile Cluster Risk" when Cluster Risk was inverted in version 0.1.0. See [Cluster Risk KPI](cluster-risk.md#change-in-version-010-higher-is-worse).

**10th and 90th percentile.** The clusters are sorted, and the one at position 10 % (or 90 %) of the count, rounded up, is taken (nearest rank, the same method as the cluster KPIs). With 20 clusters that is the 2nd lowest (or the 18th lowest). With 10 clusters or fewer it is the lowest (or the highest), the same as the worst cluster.

## Example

Three clusters with Cluster Performance scores 86.35, 98 and 50. Worst Cluster Performance is 50. With fewer than 10 clusters, the 10th percentile is also the lowest: 50.

The same example is checked by the tests in [`Management Pack/tests/test_cluster_summary_metrics.py`](../../../Management%20Pack/tests/test_cluster_summary_metrics.py).
