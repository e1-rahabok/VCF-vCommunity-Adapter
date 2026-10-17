# Cluster Consumption KPI

**Cluster Consumption** is a single 0-100 % value for a vSphere cluster. It measures actual utilization and saturation of the cluster as a whole. **Higher is worse: 0 means nothing consumed, 100 means fully consumed**, the same direction as [Cluster Risk](cluster-risk.md).

- **Cluster-wide, not the worst host.** Every sub-metric adds up the hosts of the cluster. A big host counts more than a small one. [Cluster Risk](cluster-risk.md) is the opposite: it takes the worst host.
- **Saturation is not contention.** Ballooned, swapped and zipped memory do not mean anything is slow yet. They are real consumption, so they have their own sub-metrics.

All 6 metrics are published on the cluster object under `vCommunity|Cluster Consumption`. The KPI itself is `vCommunity|Cluster Consumption|Cluster Consumption Score`.

It is one of the three inputs of the [Periodic Cluster Check](periodic-cluster-check.md).

Code: [`Management Pack/app/metrics/cluster/cluster_consumption_metrics.py`](../../../Management%20Pack/app/metrics/cluster/cluster_consumption_metrics.py)

Source of the limits: [`formula/cluster-consumption.png`](formula/cluster-consumption.png)

## The 5 sub-metrics and their limits

Every sub-metric is "lower is better", in %.

| Group | Sub-metric | Green ends at | Yellow ends at | Orange ends at | Score hits 0 at |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Utilization | Cluster-wide ESXi CPU Thread Utilization | 55 | 70 | 85 | 100 |
| Utilization | Cluster-wide ESXi Memory Consumed | 70 | 80 | 90 | 100 |
| Saturation | Cluster Memory Tiering Consumption | 4 | 8 | 16 | 32 |
| Saturation | Cluster-wide ESXi Memory Ballooned | 1 | 2 | 4 | 8 |
| Saturation | Cluster-wide ESXi Memory Zip Swap (swapped + compressed) | 0.25 | 0.5 | 1 | 2 |

The score is 100 at 0 for every row. No green range is excluded: every row with data counts in the KPI.

## How each sub-metric is calculated

The hosts that count are the running hosts with data, as in [Capacity Utilization](capacity-utilization.md#gone-hosts): a host that is disconnected, powered off, in standby or in maintenance mode is left out, so its idle capacity does not make the cluster look emptier than it is.

| Sub-metric | Cluster-wide | Source |
| :--- | :--- | :--- |
| CPU Thread Utilization | CPU threads in use on all hosts ÷ all their CPU threads. Threads in use = `cpu.utilization` % × threads, per host. | VCF Operations host stat `cpu\|utilization_average`. Threads: see [Cluster Risk](cluster-risk.md#where-each-hosts-data-comes-from). |
| Memory Consumed | Consumed memory of all hosts ÷ their DRAM | Host stats `mem\|consumed_average` / `MEM_DRAM_CAPACITY` |
| Memory Tiering Consumption | Read as it is from the cluster | VCF Operations cluster stat `mem\|tier_1_usage_percent` (NVMe Memory Usage). Only clusters with NVMe memory tiering have it; for the others it is left out. |
| Memory Ballooned | Ballooned memory of all hosts ÷ their DRAM | Host stats `mem\|vmmemctl_average` / `MEM_DRAM_CAPACITY` |
| Memory Zip Swap | Compressed plus swapped memory of all hosts ÷ their DRAM | Host stats (`mem\|compressed_average` + `mem\|swapout_average`) / `MEM_DRAM_CAPACITY` |

`MEM_DRAM_CAPACITY` is the host's DRAM only, never DRAM plus a memory tier. See [Host memory capacity](cluster-risk.md#host-memory-capacity-mem_dram_capacity).

**No extra requests.** The host stats are the ones Cluster Risk already reads in the same cycle. The cluster stat is read once per cycle for all clusters.

## How the score is calculated

The same way as every KPI, then flipped like Cluster Risk:

1. Each sub-metric value gets a score from 100 to 0, depending on the tier it is in.
2. The weighted average of the scores is a health score, where 100 is best. A sub-metric in the red tier weighs 8×, orange 4×, yellow 2×, green 1×.
3. **Cluster Consumption = 100 − that health score**, so that higher means more consumed.

Its bands are therefore those of Cluster Risk: green 0–25, yellow 25–50, orange 50–75, **red 75–100**. See [Bands: red is high](cluster-risk.md#bands-red-is-high).

## Worked example

Two hosts: a big one with 32 cores (64 threads) and 512 GB of DRAM, and a small one with 16 cores (32 threads) and 256 GB.

| | CPU Thread Utilization | Consumed | Ballooned |
| :--- | :--- | :--- | :--- |
| Big host | 40 % | 256 GB | 5.12 GB |
| Small host | 70 % | 230.4 GB | 0 |
| **Cluster-wide** | `(25.6 + 22.4) / 96 threads` = **50 %** | `486.4 / 768 GB` = **63.33 %** | `5.12 / 768 GB` = **0.67 %** |

The average of 40 % and 70 % would be 55 %. Cluster-wide is 50 %, because the big host has twice the threads.

- No memory tiering, so Memory Tiering Consumption is left out. Zip Swap is 0.
- Scores, all green with weight 1: CPU `100 − 50 / 55 × 25` = 77.27, Memory `100 − 63.33 / 70 × 25` = 77.38, Ballooned `100 − 0.67 × 25` = 83.25, Zip Swap 100.
- Health = `(77.27 + 77.38 + 83.25 + 100) / 4` = 84.48. Cluster Consumption = `100 − 84.48` = **15.52**.

The same example is checked by the tests in [`Management Pack/tests/test_cluster_consumption_metrics.py`](../../../Management%20Pack/tests/test_cluster_consumption_metrics.py).

## Missing data

A sub-metric with no data is not published for that cycle, and it is left out of the KPI. It is never counted as 0, because a value of 0 means "nothing consumed".

- If the host stats request fails, only Memory Tiering Consumption can be scored.
- A host that VCF Operations does not know is left out.

## Known limitations

- **Memory Tiering Consumption is not yet confirmed on a live system.** The lab has no NVMe memory tiering, so `mem|tier_1_usage_percent` has no value there. What it is a share of (the NVMe tier, or all memory) is to be confirmed on a cluster with memory tiering.
