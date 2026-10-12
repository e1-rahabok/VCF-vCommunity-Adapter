# Daily Cluster Check

**Daily Cluster Check** gives every vSphere cluster a **0 or 1** once a day. The result comes from the 95th percentile of the last 24 hours of Cluster Risk, Cluster Performance and cluster utilization.

The time of day is set in the account's **Advanced Settings**: see [Configuration](configuration.md#2-advanced-settings-optional).

Code: [`Management Pack/app/metrics/cluster/daily_cluster_check.py`](../Management%20Pack/app/metrics/cluster/daily_cluster_check.py)

## Known limitations

> **Read this before using the properties.**

- **Not complete yet: two placeholders.**
  - **Utilization stat keys.** The CPU and memory utilization keys of a cluster are still to be supplied (`CPU_UTILIZATION`, `MEMORY_UTILIZATION`). Until then, Cluster Utilization and Result are not published.
  - **Result rule.** The rule is a placeholder: 1 when Risk is below 50, Performance below 50, or Utilization above 80. It is to be replaced by the real rule (`decide()`).
- **The time is in UTC.** There is no time zone setting. For 02:00 in Singapore (UTC+8), enter `18:00`.
- **The result can come up to a few cycles late.** The calculation runs in the first collection cycle (every 5 minutes) after the set time. With more than 500 due clusters in one vCenter, the rest follow in the next cycles: 2,000 clusters in one vCenter take 4 cycles, about 20 minutes. The 24-hour window is still the same for all.
- **A value with no data keeps yesterday's value.** VCF Operations keeps a property until it is set again. When a stat has no data for the 24 hours, its value is not published, and the property still shows the previous day's. Check **Window End** to see which day the values are for: it is always set.
- **The Risk and Performance scores are "higher is better".** Their 95th percentile is near the best value of the day, not the worst. A bad hour does not show in it. The 5th percentile would show bad hours. The 95th was asked for, and is used.
- **A cluster added during the day is calculated over the history it has.** Fewer than 288 samples, but still a 95th percentile.

## The properties

On every vSphere cluster, under `vCommunity|Daily Cluster Check`. Properties, not metrics: one value a day.

| Property | Calculation |
| :--- | :--- |
| `95th Percentile Cluster Risk` (%) | 95th percentile of `vCommunity\|Cluster Risk\|Cluster Risk Score` over the 24 hours. |
| `95th Percentile Cluster Performance` (%) | 95th percentile of `vCommunity\|Cluster Performance\|Cluster Performance Score` over the 24 hours. |
| `95th Percentile Cluster Utilization` (%) | max(95th percentile of CPU utilization, 95th percentile of memory utilization). |
| `Result` | 0 or 1, from the three values above. Not published when one of them has no data. |
| `Window End` | The end of the 24 hours, such as `2026-10-12 00:00 UTC`. |

**Percentile.** Nearest-rank, as in the KPIs: sort the samples and take the one at position 95 % of the count, rounded up. A full day has 288 five-minute samples, so it is the 274th lowest: the 14 highest samples (70 minutes) are ignored.

**Inputs**, all from VCF Operations: the 5-minute history of the four stats. Nothing is read from vCenter.

## How it runs

1. Every cycle, the cluster collection reads the `Window End` property of the clusters of its vCenter. One request per 1,000 clusters.
2. The latest window end is the last time the clock passed the set time: today's, or yesterday's when today's time has not come yet.
3. A cluster is **due** when its `Window End` is not the latest window end. After the set time, every cluster is due.
4. At most 500 due clusters are read per cycle, 100 per request: 24 hours of 5-minute samples, for the four stats.
5. The properties are published, `Window End` last. The cluster is no longer due until the next day.
6. A cluster whose request failed is not published, so it stays due, and the next cycle tries again.

## Design considerations

- **The 95th percentile is calculated in code.** VCF Operations roll-ups have AVG, MAX, MIN and SUM, but no percentile. An estimate from Max and Avg is driven by the Max: one spike in a quiet day decides it. With a 0/1 result that is a wrong answer, not a small error.
- **The 24 hours end at the set time, not when the calculation runs.** Every cluster has the same window, even when it is calculated a few cycles later.
- **The state is in VCF Operations, not in the adapter.** The `Window End` property says which day a cluster was calculated for. A restart or an upgrade of the pack loses nothing, and needs no file in the container.
- **Spread over cycles.** At most 500 clusters per vCenter per cycle, so the history is not read all at once. Each account reads only the clusters of its own vCenter.
- **Changing the time makes every cluster due again**, because the latest window end changes. They are recalculated for the new window in the next cycles.
- **Load.** 24 hours of 5-minute samples is 288 per stat, 4 stats per cluster: about 1,150 values per cluster, 2.3 million for 2,000 clusters, once a day. A dashboard or report over 2,000 objects for 24 hours reads a similar amount.

## Example

A cluster with a quiet day of Cluster Risk at 90 %, and one 5-minute dip to 20 %: the 95th percentile is 90 %. With CPU utilization at 40 % and memory at 70 %, Cluster Utilization is 70 %.

The same cases are checked by the tests in [`Management Pack/tests/test_daily_cluster_check.py`](../Management%20Pack/tests/test_daily_cluster_check.py).
