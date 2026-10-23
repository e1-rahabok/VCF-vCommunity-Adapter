# Periodic Cluster Check

**Periodic Cluster Check** sets **Close for Business** on every vSphere cluster once per period: every 24 hours by default. It marks whether the cluster is open to accept new VMs:

- **1: closed for business.** The cluster is full. Do not place new VMs on it.
- **0: open.** The cluster can accept new VMs.

It is decided from the worst part of the last period of the three cluster KPIs: [Cluster Performance](cluster-performance.md), [Cluster Risk](cluster-risk.md) and [Cluster Consumption](cluster-consumption.md). See [The rule](#the-rule).

## Settings

Three settings in the account's **Advanced Settings** (see [Configuration](../../configuration-guide/adapter-instance.md#2-advanced-settings-optional)):

| Setting | Values | Default | Meaning |
| :--- | :--- | :--- | :--- |
| **Cluster Check Period (hours)** | 1, 2, 4, 6, 8, 12, 24 | 24 | How long each window is, and how often it is calculated. |
| **Cluster Check Time (UTC)** | HH:MM | 00:00 | When one window ends. The others end every period from it. |
| **Cluster Check Worst Percent** | 0 to 50 | 5 | How much of the window's worst end is ignored. See [Worst](#worst). |

Each period divides a day, so the windows end at the same times every day. Each window is as long as the period, so every hour is covered exactly once.

| Period | Time | Windows end at (UTC) | Each covers |
| :--- | :--- | :--- | :--- |
| 24 | 00:00 | 00:00 | the 24 hours before |
| 6 | 00:00 | 00:00, 06:00, 12:00, 18:00 | the 6 hours before |
| 8 | 10:00 | 02:00, 10:00, 18:00 | the 8 hours before |
| 1 | 00:15 | every hour at :15 | the hour before |

Code: [`Management Pack/app/metrics/cluster/periodic_cluster_check.py`](../../../Management%20Pack/app/metrics/cluster/periodic_cluster_check.py)

## Known limitations

> **Read this before using the metrics.**

- **The first window after installing has less history.** Cluster Consumption is calculated from the first collection, so the first check covers only the hours since then.
- **A short period is less stable.** A 1-hour window has 12 five-minute samples. With the default of 5 %, nothing is ignored (5 % of 12 rounds down to 0 samples): the single worst sample decides.
- **The time is in UTC.** There is no time zone setting. For 02:00 in Singapore (UTC+8), enter `18:00`.
- **The result can come up to a few cycles late.** The calculation runs in the first collection cycle (every 5 minutes) after a window ends. With more than 500 due clusters in one vCenter, the rest follow in the next cycles: 2,000 clusters in one vCenter take 4 cycles, about 20 minutes. The window is still the same for all.
- **A value with no data leaves a gap.** When a KPI has no data for the window, its metric is not published for that window, so the chart has no point there. The time of a point is when it was calculated: just after its window ended.
- **Close for Business is not published when one of the three values has no data.** That window has no point (see above).
- **One point per period.** The values are metrics produced once per period, not every 5 minutes. A chart of a day with a 24-hour period has one point.
- **A cluster added during a window is calculated over the history it has.** Fewer samples, but still a percentile.

## The metrics

On every vSphere cluster, under `vCommunity|Periodic Cluster Check`. **Metrics**: numbers produced once per period, a fixed interval. There are no properties: every cluster has the same window and settings, which are the account's, and the log states them for each calculation.

| Key | Calculation |
| :--- | :--- |
| `Worst Cluster Performance` (metric) (%) | The worst end of `vCommunity\|Cluster Performance\|Cluster Performance Score` over the window: its low end, because higher is better. |
| `Worst Cluster Risk` (metric) (%) | The worst end of `vCommunity\|Cluster Risk\|Cluster Risk Score` over the window: its high end, because higher is worse. |
| `Worst Cluster Consumption` (metric) (%) | The worst end of `vCommunity\|Cluster Consumption\|Cluster Consumption Score` over the window: its high end, because higher is worse. |
| `Close for Business` (metric) | 1: the cluster is full, do not place new VMs. 0: open. From the three values above, see [The rule](#the-rule). Not published when one of them has no data. |

### Worst

Each KPI is summarised by its worst end: the value with only the **Worst Percent** of the window's samples worse than it. With the default of 5 % and a 24-hour window of 288 five-minute samples, the 14 worst samples (70 minutes) are ignored:

| KPI | Worse is | With 5 % | With 0 % |
| :--- | :--- | :--- | :--- |
| Cluster Performance | lower | the 5th percentile: the 14 lowest samples are ignored | the lowest sample |
| Cluster Risk, Cluster Consumption | higher | the 95th percentile: the 14 highest samples are ignored | the highest sample |

- **0** is the single worst sample: one bad 5-minute sample decides.
- **50** is the middle (median) of the window. A higher value would summarise the window by its better half, so 50 is the maximum.
- **Percentile.** Nearest-rank, as in the KPIs: sort the samples and take the one at position (100 − Worst Percent) % of the count, rounded up, counted from the best end.

## The rule

Each of the three values gets the colour of the KPI bands:

| Band | Cluster Performance (higher is better) | Cluster Risk, Cluster Consumption (higher is worse) |
| :--- | :--- | :--- |
| Green | 75 – 100 | 0 – 25 |
| Yellow | 50 – 75 | 25 – 50 |
| Orange | 25 – 50 | 50 – 75 |
| **Red** | **0 – 25** | **75 – 100** |

A value on a limit belongs to the better band: Performance of exactly 25 is orange, Risk of exactly 75 is orange.

Close for Business is **1** when either rule matches, else **0**:

| Rule | Condition | Meaning |
| :--- | :--- | :--- |
| 1 | Consumption is red, **or** Performance is red. | The cluster is full, or its VMs already suffer. |
| 2 | Consumption and Performance are **both orange**, **and** Risk is orange or red. | Busy and slow at once, and heading the wrong way. |

**Risk never closes a cluster on its own.** It is a leading indicator: it buys time. It decides only when Consumption and Performance are both orange. Orange is the lower Risk threshold of a critical cluster, and it is used for every cluster. See [Closing the cluster](../../concepts/capacity-management.md#closing-the-cluster).

| Worst Performance | Worst Risk | Worst Consumption | Close for Business |
| :--- | :--- | :--- | :--- |
| 20 | 10 | 30 | 1 (rule 1: Performance red) |
| 90 | 10 | 80 | 1 (rule 1: Consumption red) |
| 40 | 60 | 60 | 1 (rule 2: both orange, Risk orange) |
| 40 | 90 | 60 | 1 (rule 2: both orange, Risk red) |
| 40 | 40 | 60 | 0 (both orange, but Risk is yellow) |
| 90 | 90 | 30 | 0 (Risk red alone does not close) |
| 40 | 90 | 40 | 0 (Consumption is yellow, so Risk is not looked at) |
| 25 | 10 | 10 | 0 (25 is orange, not red) |
| 90 | 10 | 30 | 0 (healthy) |

The rule is in `decide()` and `band()`, in the code.

**Inputs**, all from VCF Operations: the 5-minute history of the three KPI scores. Nothing is read from vCenter.

## How it runs

1. Every cycle, the cluster collection reads the time of the latest sample of these metrics, and of the three KPIs, for the clusters of its vCenter. One request per 1,000 clusters.
2. The latest window end is the last window end at or before now: the set time, or a whole number of periods after it.
3. A cluster is **due** when its latest Periodic Cluster Check metric is older than the latest window end, and a KPI has data in that window. After a window ends, every cluster with KPI data is due. A cluster without any KPI data is not, so it is not read every cycle.
4. At most 500 due clusters are read per cycle, 100 per request: the window's 5-minute samples, for the three KPIs.
5. The metrics are published. Their timestamp is after the window end, so the cluster is no longer due until the next window ends.
6. A cluster whose request failed is not published, so it stays due, and the next cycle tries again.

## Design considerations

- **Three KPIs on the same 0-100 scale.** Performance, Risk and Consumption use the same bands, so the rule reads the same colours for all three.
- **The worst end, not the average.** A cluster that is bad for an hour a day is not fine for new VMs. The worst percent ignores short spikes, but not a sustained problem.
- **The percentile is calculated in code.** VCF Operations roll-ups have AVG, MAX, MIN and SUM, but no percentile. An estimate from Max and Avg is driven by the Max: one spike in a quiet day decides it. With a 0/1 result that is a wrong answer, not a small error.
- **A window ends at a fixed time, not when the calculation runs.** Every cluster has the same window, even when it is calculated a few cycles later.
- **No state is stored.** The timestamps of the published metrics say whether a cluster was calculated for the latest window. Nothing is kept in the adapter or stored per cluster, so a restart of the pack loses nothing.
- **Spread over cycles.** At most 500 clusters per vCenter per cycle, so the history is not read all at once. Each account reads only the clusters of its own vCenter.
- **A changed setting applies from the next window.** A window already calculated is not recalculated.
- **Load.** 24 hours of 5-minute samples is 288 per stat, 3 stats per cluster: about 860 values per cluster, 1.7 million for 2,000 clusters, once a day. A shorter period reads the same total per day, in smaller pieces. A dashboard or report over 2,000 objects for 24 hours reads a similar amount.

## Example

A cluster with a quiet 24-hour window of Cluster Performance at 90 %, and one 5-minute dip to 20 %. With the default of 5 %, the dip is one of the 14 samples ignored: Worst Cluster Performance is 90 %, green. With Cluster Risk at 80 % (red) and Cluster Consumption at 60 % (orange) all day, nothing but Risk is red, and Performance is not orange: Close for Business is 0.

With Worst Percent set to 0, the dip decides: Worst Cluster Performance is 20 %, red, and Close for Business is 1.

The same cases are checked by the tests in [`Management Pack/tests/test_periodic_cluster_check.py`](../../../Management%20Pack/tests/test_periodic_cluster_check.py).
