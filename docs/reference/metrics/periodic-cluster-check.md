# Periodic Cluster Check

The **Periodic Cluster Check** sets **Close for Business** on every vSphere cluster once per period, every 24 hours by default. The value says whether the cluster should take new VMs:

- **1, closed for business.** The cluster is full. Do not place new VMs on it.
- **0, open.** The cluster can take new VMs.

The decision uses the worst part of the last period of the three cluster KPIs, and closes only on values clearly inside the red or orange band: [Cluster Performance](cluster-performance.md), [Cluster Risk](cluster-risk.md) and [Cluster Consumption](cluster-consumption.md). See [The rule](#the-rule).

Code: [`Management Pack/app/metrics/cluster/periodic_cluster_check.py`](../../../Management%20Pack/app/metrics/cluster/periodic_cluster_check.py)

## Settings

Three settings under **Advanced Settings** of the [Adapter Instance](../../configuration-guide/adapter-instance.md#2-advanced-settings-optional):

| Setting | Values | Default | Meaning |
| :--- | :--- | :--- | :--- |
| **Cluster Check Period (hours)** | 1, 2, 4, 6, 8, 12, 24 | 24 | The length of each window, and how often the check runs. |
| **Cluster Check Time (UTC)** | HH:MM | 00:00 | When one window ends. The other windows end every period from it. An empty or invalid value uses 00:00. |
| **Cluster Check Worst Percent** | 0 to 50 | 5 | How much of the worst end of the window is ignored. See [Worst](#worst). |

Each period divides a day, so the windows end at the same times every day. Each window is as long as the period, so every hour is covered exactly once.

| Period | Time | Windows end at (UTC) | Each covers |
| :--- | :--- | :--- | :--- |
| 24 | 00:00 | 00:00 | the 24 hours before |
| 6 | 00:00 | 00:00, 06:00, 12:00, 18:00 | the 6 hours before |
| 8 | 10:00 | 02:00, 10:00, 18:00 | the 8 hours before |
| 1 | 00:15 | every hour at :15 | the hour before |

## Known limitations

> **Read this before you use the metrics.**

- **The first window after installation has less history.** Cluster Consumption is calculated from the first collection, so the first check covers only the hours since then.
- **A short period is less stable.** A 1-hour window has 12 five-minute samples. With the default of 5 %, nothing is ignored, because 5 % of 12 rounds down to 0 samples. The single worst sample decides.
- **The time is in UTC.** There is no time zone setting. For 02:00 in Singapore (UTC+8), enter `18:00`.
- **The result can be a few cycles late.** The check runs in the first collection cycle after a window ends. With more than 500 due clusters in one vCenter, the rest follow in the next cycles: 2,000 clusters in one vCenter take 4 cycles, about 20 minutes. The window is the same for all of them.
- **No data leaves a gap.** When a KPI has no data for the window, its metric is not published for that window, so the chart has no point there. A point is timestamped when it is calculated, just after its window ends.
- **Close for Business is not published when one of the three values has no data.** That window has no point.
- **One point per period.** The values are published once per period, not every 5 minutes. A one-day chart with a 24-hour period has one point.
- **A cluster added during a window is calculated over the history it has.** It has fewer samples, but the result is still a percentile.

## The metrics

All four are metrics on every vSphere cluster, under `vCommunity|Periodic Cluster Check`, published once per period. There are no properties: every cluster of an Adapter Instance has the same window and settings, and the adapter log states them for each calculation.

| Key | Calculation |
| :--- | :--- |
| `Worst Cluster Performance` (%) | The worst end of `vCommunity\|Cluster Performance\|Cluster Performance Score` over the window. That is its low end, because higher is better. |
| `Worst Cluster Risk` (%) | The worst end of `vCommunity\|Cluster Risk\|Cluster Risk Score` over the window. That is its high end, because higher is worse. |
| `Worst Cluster Consumption` (%) | The worst end of `vCommunity\|Cluster Consumption\|Cluster Consumption Score` over the window: its high end. |
| `Close for Business` | 1 when the cluster is full and should take no new VMs, 0 when it is open. Decided from the three values above, see [The rule](#the-rule). Not published when one of them has no data. |

The number of clusters whose Close for Business changed since the previous window is on the vSphere World object. See [Close for Business changes](vsphere-world-metrics.md#close-for-business-changes).

### Worst

Each KPI is summarized by its worst end: the value that only **Worst Percent** of the window's samples are worse than. With the default of 5 % and a 24-hour window of 288 five-minute samples, the 14 worst samples (70 minutes) are ignored:

| KPI | Worse is | With 5 % | With 0 % |
| :--- | :--- | :--- | :--- |
| Cluster Performance | lower | the 5th percentile: the 14 lowest samples are ignored | the lowest sample |
| Cluster Risk, Cluster Consumption | higher | the 95th percentile: the 14 highest samples are ignored | the highest sample |

- **0** takes the single worst sample, so one bad 5-minute sample decides.
- **50** takes the median of the window. A higher value would summarize the window by its better half, so 50 is the maximum.
- The percentile uses the nearest-rank method, as the KPIs do: the samples are sorted, and the one at position (100 − Worst Percent) % of the count, rounded up and counted from the best end, is taken.

## The rule

Each of the three values has the color of its KPI band. This is the color shown on screen:

| Band | Cluster Performance (higher is better) | Cluster Risk, Cluster Consumption (higher is worse) |
| :--- | :--- | :--- |
| Green | 75 – 100 | 0 – 25 |
| Yellow | 50 – 75 | 25 – 50 |
| Orange | 25 – 50 | 50 – 75 |
| **Red** | **0 – 25** | **75 – 100** |

Closing a cluster needs more than a value just across a band limit. The closure levels sit inside the bands, so a value must be clearly red or clearly orange:

| Closure level | Cluster Performance | Cluster Risk, Cluster Consumption |
| :--- | :--- | :--- |
| Red | below 20 (red on screen starts below 25) | above 80 (red on screen starts above 75) |
| Orange | below 40 (orange on screen starts below 50) | above 60 (orange on screen starts above 50) |

A value on a closure level does not reach it: a Performance of exactly 20 is orange for closure, and a Consumption of exactly 80 is orange.

Close for Business is **1** when either rule matches, and **0** otherwise. Red and orange here are the closure levels:

| Rule | Condition | Meaning |
| :--- | :--- | :--- |
| 1 | Consumption is red, **or** Performance is red. | The cluster is full, or its VMs already have contention. |
| 2 | Consumption and Performance are **both orange**, **and** Risk is orange or red. | The cluster is busy and its VMs are slowing down, and the leading indicators are getting worse. |

Risk never closes a cluster on its own. It is a leading indicator, so it decides only when Consumption and Performance are both orange. The threshold is orange for every cluster, which is the lower Risk threshold that the capacity model uses for a critical cluster. See [Closing the cluster](../../concepts/capacity-management.md#closing-the-cluster).

| Performance | Risk | Consumption | Close for Business |
| :--- | :--- | :--- | :--- |
| 15 | 10 | 30 | 1 (rule 1: Performance red) |
| 90 | 10 | 85 | 1 (rule 1: Consumption red) |
| 35 | 65 | 65 | 1 (rule 2: both orange, Risk orange) |
| 35 | 90 | 65 | 1 (rule 2: both orange, Risk red) |
| 35 | 55 | 65 | 0 (both orange, but Risk is not above 60) |
| 90 | 90 | 30 | 0 (Risk red on its own does not close) |
| 35 | 90 | 45 | 0 (Consumption is not above 60, so Risk is not used) |
| 22 | 10 | 10 | 0 (22 shows red on screen, but closure red is below 20) |
| 90 | 10 | 78 | 0 (78 shows red on screen, but closure red is above 80) |
| 90 | 10 | 30 | 0 (healthy) |

The rule is in `decide()` and `closure_level()` in the code.

The inputs all come from VCF Operations: the 5-minute history of the three KPI scores. Nothing is read from vCenter.

## How it runs

1. Every cycle, the cluster collection reads the time of the latest sample of these metrics, and of the three KPIs, for the clusters of its vCenter. One request covers up to 1,000 clusters.
2. The latest window end is the last window end at or before now: the set time, or a whole number of periods after it.
3. A cluster is due when its latest Periodic Cluster Check metric is older than the latest window end, and a KPI has data in that window. After a window ends, every cluster with KPI data is due. A cluster without any KPI data is not due, so it is not read every cycle.
4. At most 500 due clusters are read per cycle, 100 per request: the window's 5-minute samples of the three KPIs.
5. The metrics are published. Their timestamp is after the window end, so the cluster is not due again until the next window ends.
6. A cluster whose request failed is not published. It stays due, and the next cycle tries again.

## Design considerations

- **Three KPIs on the same 0 to 100 scale.** Performance, Risk and Consumption use the same bands, so the rule reads the same colors for all three.
- **Closure levels inside the bands.** A value just across a band limit can cross back after a few VMs move. Closing needs a value clearly inside the band, so a cluster does not flip between open and closed on a small change.
- **The worst end of the window is used.** An average would hide a problem: a cluster that is in trouble for an hour every day should not take new VMs. The Worst Percent ignores short spikes, but not a sustained problem.
- **The percentile is calculated in code.** VCF Operations roll-ups offer AVG, MAX, MIN and SUM, but no percentile. An estimate from Max and Avg is driven by the Max, so one spike in a quiet day would decide, and with a 0 or 1 result that is a wrong answer rather than a small error.
- **Windows end at fixed times.** The end does not depend on when the calculation runs, so every cluster has the same window, even when it is calculated a few cycles later.
- **No state is stored.** The timestamps of the published metrics show whether a cluster was calculated for the latest window. Nothing is kept in the adapter, so a restart of the pack loses nothing.
- **Spread over cycles.** At most 500 clusters per vCenter per cycle, so the history is not read all at once. Each Adapter Instance reads only the clusters of its own vCenter.
- **A changed setting applies from the next window.** A window already calculated is not recalculated.
- **Load.** 24 hours of 5-minute samples is 288 values per stat. With 3 stats per cluster that is about 860 values per cluster, or 1.7 million for 2,000 clusters, once a day. A shorter period reads the same total per day in smaller pieces. A dashboard or report over 2,000 objects for 24 hours reads a similar amount.

## Example

A cluster has a quiet 24-hour window with Cluster Performance at 90 %, and one 5-minute dip to 15 %. With the default of 5 %, the dip is one of the 14 ignored samples, so Worst Cluster Performance is 90 %, green. Cluster Risk is 85 % (red) and Cluster Consumption 65 % (orange for closure) all day. Only Risk is red, and Performance is not orange, so Close for Business is 0.

With Worst Percent set to 0, the dip decides: Worst Cluster Performance is 15 %, red for closure, and Close for Business is 1. A dip to 22 % would show red on screen but would not close the cluster, because closure red is below 20.

The tests in [`Management Pack/tests/test_periodic_cluster_check.py`](../../../Management%20Pack/tests/test_periodic_cluster_check.py) check the same cases.
