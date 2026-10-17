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

> **Read this before using the properties.**

- **The first window after installing has less history.** Cluster Consumption is calculated from the first collection, so the first check covers only the hours since then.
- **A short period is less stable.** A 1-hour window has 12 five-minute samples. With the default of 5 %, nothing is ignored (5 % of 12 rounds down to 0 samples): the single worst sample decides.
- **The time is in UTC.** There is no time zone setting. For 02:00 in Singapore (UTC+8), enter `18:00`.
- **The result can come up to a few cycles late.** The calculation runs in the first collection cycle (every 5 minutes) after a window ends. With more than 500 due clusters in one vCenter, the rest follow in the next cycles: 2,000 clusters in one vCenter take 4 cycles, about 20 minutes. The window is still the same for all.
- **A value with no data keeps the previous window's value.** VCF Operations keeps a property until it is set again. When a KPI has no data for the window, its value is not published, and the property still shows the previous window's. Check **Window End** to see which window the values are for: it is always set.
- **Close for Business is not published when one of the three values has no data.** It keeps the previous window's value, like every property (see above).
- **A cluster added during a window is calculated over the history it has.** Fewer samples, but still a percentile.

## The properties

On every vSphere cluster, under `vCommunity|Periodic Cluster Check`. Properties, not metrics: one value per window.

| Property | Calculation |
| :--- | :--- |
| `Worst Cluster Performance` (%) | The worst end of `vCommunity\|Cluster Performance\|Cluster Performance Score` over the window: its low end, because higher is better. |
| `Worst Cluster Risk` (%) | The worst end of `vCommunity\|Cluster Risk\|Cluster Risk Score` over the window: its high end, because higher is worse. |
| `Worst Cluster Consumption` (%) | The worst end of `vCommunity\|Cluster Consumption\|Cluster Consumption Score` over the window: its high end, because higher is worse. |
| `Close for Business` | 1: the cluster is full, do not place new VMs. 0: open. From the three values above, see [The rule](#the-rule). Not published when one of them has no data. |
| `Worst Percent` | The Cluster Check Worst Percent the values were calculated with. |
| `Window Hours` | The length of the window, in hours: the Cluster Check Period when it was calculated. |
| `Window End` | The end of the window, such as `2026-10-12 00:00 UTC`. |

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
| 1 | **Any** of the three is red. | One of them is already bad enough on its own. |
| 2 | **All three** are orange. | Slow, at risk and busy, all at once. |

| Worst Performance | Worst Risk | Worst Consumption | Close for Business |
| :--- | :--- | :--- | :--- |
| 20 | 10 | 30 | 1 (rule 1: Performance red) |
| 90 | 80 | 30 | 1 (rule 1: Risk red) |
| 90 | 10 | 80 | 1 (rule 1: Consumption red) |
| 40 | 60 | 60 | 1 (rule 2: all three orange) |
| 40 | 60 | 40 | 0 (Consumption is yellow) |
| 25 | 10 | 10 | 0 (25 is orange, not red) |
| 90 | 10 | 30 | 0 (healthy) |

The rule is in `decide()` and `band()`, in the code.

**Inputs**, all from VCF Operations: the 5-minute history of the three KPI scores. Nothing is read from vCenter.

## How it runs

1. Every cycle, the cluster collection reads the `Window End`, `Window Hours` and `Worst Percent` properties of the clusters of its vCenter. One request per 1,000 clusters.
2. The latest window end is the last window end at or before now: the set time, or a whole number of periods after it.
3. A cluster is **due** when its `Window End` is not the latest window end, its `Window Hours` is not the period, or its `Worst Percent` is not the setting. After a window ends, every cluster is due.
4. At most 500 due clusters are read per cycle, 100 per request: the window's 5-minute samples, for the three KPIs.
5. The properties are published, `Worst Percent`, `Window Hours` and `Window End` last. The cluster is no longer due until the next window ends.
6. A cluster whose request failed is not published, so it stays due, and the next cycle tries again.

## Design considerations

- **Three KPIs on the same 0-100 scale.** Performance, Risk and Consumption share the same bands, so one rule covers all three.
- **The worst end, not the average.** A cluster that is bad for an hour a day is not fine for new VMs. The worst percent ignores short spikes, but not a sustained problem.
- **The percentile is calculated in code.** VCF Operations roll-ups have AVG, MAX, MIN and SUM, but no percentile. An estimate from Max and Avg is driven by the Max: one spike in a quiet day decides it. With a 0/1 result that is a wrong answer, not a small error.
- **A window ends at a fixed time, not when the calculation runs.** Every cluster has the same window, even when it is calculated a few cycles later.
- **The state is in VCF Operations, not in the adapter.** The `Window End`, `Window Hours` and `Worst Percent` properties say which window and setting a cluster was calculated for. A restart of the pack loses nothing, and needs no file in the container.
- **Spread over cycles.** At most 500 clusters per vCenter per cycle, so the history is not read all at once. Each account reads only the clusters of its own vCenter.
- **Changing a setting makes every cluster due again**, because the window or its summary changes. They are recalculated in the next cycles.
- **Load.** 24 hours of 5-minute samples is 288 per stat, 3 stats per cluster: about 860 values per cluster, 1.7 million for 2,000 clusters, once a day. A shorter period reads the same total per day, in smaller pieces. A dashboard or report over 2,000 objects for 24 hours reads a similar amount.

## Example

A cluster with a quiet 24-hour window of Cluster Performance at 90 %, and one 5-minute dip to 20 %. With the default of 5 %, the dip is one of the 14 samples ignored: Worst Cluster Performance is 90 %, green. With Cluster Risk at 40 % (yellow) and Cluster Consumption at 60 % (orange) all day, nothing is red and not all three are orange: Close for Business is 0.

With Worst Percent set to 0, the dip decides: Worst Cluster Performance is 20 %, red, and Close for Business is 1.

The same cases are checked by the tests in [`Management Pack/tests/test_periodic_cluster_check.py`](../../../Management%20Pack/tests/test_periodic_cluster_check.py).
