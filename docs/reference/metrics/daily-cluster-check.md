# Daily Cluster Check

**Daily Cluster Check** sets **Close for Business** on every vSphere cluster once per period: every 24 hours by default. It marks whether the cluster is open to accept new VMs:

- **1: closed for business.** The cluster is full. Do not place new VMs on it.
- **0: open.** The cluster can accept new VMs.

It is decided from the last period of Capacity Utilization, Cluster Performance and Cluster Risk. See [The rule](#the-rule).

## Settings

Two settings in the account's **Advanced Settings** (see [Configuration](../../configuration-guide/adapter-instance.md#2-advanced-settings-optional)):

| Setting | Values | Default | Meaning |
| :--- | :--- | :--- | :--- |
| **Cluster Check Period (hours)** | 1, 2, 4, 6, 8, 12, 24 | 24 | How long each window is, and how often it is calculated. |
| **Cluster Check Time (UTC)** | HH:MM | 00:00 | When one window ends. The others end every period from it. |

**Upgrade from 0.1.0 or 0.1.1.** The drop-down values are now "01" to "24", so they sort as numbers. An account saved with a period other than 24 keeps working with that period. Its drop-down may show "--Select--" until you choose the period again.

Each period divides a day, so the windows end at the same times every day. Each window is as long as the period, so every hour is covered exactly once.

| Period | Time | Windows end at (UTC) | Each covers |
| :--- | :--- | :--- | :--- |
| 24 | 00:00 | 00:00 | the 24 hours before |
| 6 | 00:00 | 00:00, 06:00, 12:00, 18:00 | the 6 hours before |
| 8 | 10:00 | 02:00, 10:00, 18:00 | the 8 hours before |
| 1 | 00:15 | every hour at :15 | the hour before |

Code: [`Management Pack/app/metrics/cluster/daily_cluster_check.py`](../../../Management%20Pack/app/metrics/cluster/daily_cluster_check.py)

## Known limitations

> **Read this before using the properties.**

- **Capacity Utilization has its own limitations**, among them: all hosts of a cluster are assumed to be the same size, and it can be above 100 %. See [Capacity Utilization](capacity-utilization.md#known-limitations).
- **The first window after the upgrade has less history.** Capacity Utilization is a new metric, so the first check after the upgrade covers only the hours since then.
- **A short period is less stable.** A 1-hour window has 12 five-minute samples. Its 95th percentile is then the 12th lowest, the highest sample, and its 99th percentile too: one spike decides it.
- **The time is in UTC.** There is no time zone setting. For 02:00 in Singapore (UTC+8), enter `18:00`.
- **The result can come up to a few cycles late.** The calculation runs in the first collection cycle (every 5 minutes) after a window ends. With more than 500 due clusters in one vCenter, the rest follow in the next cycles: 2,000 clusters in one vCenter take 4 cycles, about 20 minutes. The window is still the same for all.
- **A value with no data keeps the previous window's value.** VCF Operations keeps a property until it is set again. When a stat has no data for the window, its value is not published, and the property still shows the previous window's. Check **Window End** to see which window the values are for: it is always set.
- **Cluster Performance is "higher is better".** Its 95th percentile is near the best value of the window, not the worst. A bad hour does not show in it; the 5th percentile would show it. The 95th was asked for, and is used. Cluster Risk is "higher is worse", so its 95th percentile is the bad end of the window, as intended.
- **Close for Business is not published when one of the three values has no data.** It keeps the previous window's value, like every property (see above).
- **A cluster added during a window is calculated over the history it has.** Fewer samples, but still a percentile.

## The properties

On every vSphere cluster, under `vCommunity|Daily Cluster Check`. Properties, not metrics: one value per window.

| Property | Calculation |
| :--- | :--- |
| `99th Percentile Capacity Utilization` (%) | max(99th percentile of `vCommunity\|Capacity\|CPU Utilization`, 99th percentile of `vCommunity\|Capacity\|Memory Utilization`) over the window. See [Capacity Utilization](capacity-utilization.md). Can be above 100 %. |
| `95th Percentile Cluster Performance` (%) | 95th percentile of `vCommunity\|Cluster Performance\|Cluster Performance Score` over the window. Higher is better. |
| `95th Percentile Cluster Risk` (%) | 95th percentile of `vCommunity\|Cluster Risk\|Cluster Risk Score` over the window. Higher is worse. |
| `Close for Business` | 1: the cluster is full, do not place new VMs. 0: open. From the three values above, see [The rule](#the-rule). Not published when one of them has no data. |
| `Window Hours` | The length of the window, in hours: the Cluster Check Period when it was calculated. |
| `Window End` | The end of the window, such as `2026-10-12 00:00 UTC`. |

**Percentile.** Nearest-rank, as in the KPIs: sort the samples and take the one at position 95 % (or 99 %) of the count, rounded up. A 24-hour window has 288 five-minute samples:

- 95th percentile: the 274th lowest. The 14 highest samples (70 minutes) are ignored.
- 99th percentile: the 286th lowest. The 2 highest samples (10 minutes) are ignored.

## The rule

Close for Business is **1** when either rule matches, else **0**.

| Rule | Condition | Meaning |
| :--- | :--- | :--- |
| 1 | Capacity Utilization > 95 **or** Cluster Performance < 25 | The cluster is full, or its VMs already suffer. |
| 2 | Capacity Utilization > 75 **and** Cluster Performance < 50 **and** Cluster Risk > 75 | Busy, slow and at risk, all three at once. |

- Capacity Utilization is the 99th percentile; Cluster Performance and Cluster Risk are the 95th percentile.
- The comparisons are strict: a value equal to a limit does not cross it. Utilization of exactly 95 does not match rule 1.

| Capacity Utilization | Cluster Performance | Cluster Risk | Close for Business |
| :--- | :--- | :--- | :--- |
| 96 | 99 | 0 | 1 (rule 1: full) |
| 10 | 24 | 0 | 1 (rule 1: VMs suffer) |
| 80 | 40 | 80 | 1 (rule 2) |
| 80 | 40 | 70 | 0 (Risk not above 75) |
| 80 | 60 | 80 | 0 (Performance not below 50) |
| 50 | 95 | 10 | 0 (healthy) |

The limits are in `decide()` and the constants above it, in the code.

**Inputs**, all from VCF Operations: the 5-minute history of the four stats. Nothing is read from vCenter.

## How it runs

1. Every cycle, the cluster collection reads the `Window End` and `Window Hours` properties of the clusters of its vCenter. One request per 1,000 clusters.
2. The latest window end is the last window end at or before now: the set time, or a whole number of periods after it.
3. A cluster is **due** when its `Window End` is not the latest window end, or its `Window Hours` is not the period. After a window ends, every cluster is due.
4. At most 500 due clusters are read per cycle, 100 per request: the window's 5-minute samples, for the four stats.
5. The properties are published, `Window Hours` and `Window End` last. The cluster is no longer due until the next window ends.
6. A cluster whose request failed is not published, so it stays due, and the next cycle tries again.

## Design considerations

- **The 95th percentile is calculated in code.** VCF Operations roll-ups have AVG, MAX, MIN and SUM, but no percentile. An estimate from Max and Avg is driven by the Max: one spike in a quiet day decides it. With a 0/1 result that is a wrong answer, not a small error.
- **A window ends at a fixed time, not when the calculation runs.** Every cluster has the same window, even when it is calculated a few cycles later.
- **The state is in VCF Operations, not in the adapter.** The `Window End` and `Window Hours` properties say which window a cluster was calculated for. A restart or an upgrade of the pack loses nothing, and needs no file in the container.
- **Spread over cycles.** At most 500 clusters per vCenter per cycle, so the history is not read all at once. Each account reads only the clusters of its own vCenter.
- **Changing the time or the period makes every cluster due again**, because the window changes. After the upgrade that added the period, every cluster is due once, because `Window Hours` is new. They are recalculated for the new window in the next cycles.
- **Load.** 24 hours of 5-minute samples is 288 per stat, 4 stats per cluster: about 1,150 values per cluster, 2.3 million for 2,000 clusters, once a day. A shorter period reads the same total per day, in smaller pieces: 24 windows of 1 hour read as much as one of 24 hours. A dashboard or report over 2,000 objects for 24 hours reads a similar amount.

## Example

A cluster with a quiet 24-hour window of Cluster Performance at 90 %, and one 5-minute dip to 20 %: the 95th percentile is 90 %. With CPU utilization at 40 % and memory at 70 % all day, Capacity Utilization is 70 %. Rule 1 does not match (70 is not above 95, 90 is not below 25), and rule 2 does not match (90 is not below 50): Close for Business is 0.

The same cases are checked by the tests in [`Management Pack/tests/test_daily_cluster_check.py`](../../../Management%20Pack/tests/test_daily_cluster_check.py).
