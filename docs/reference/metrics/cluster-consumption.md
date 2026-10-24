# Cluster Consumption KPI

**Cluster Consumption** is a single 0-100 % value for a vSphere cluster. It measures actual utilization and saturation of the cluster as a whole, **against its usable capacity**. **Higher is worse: 0 means nothing consumed, 100 means fully consumed**, the same direction as [Cluster Risk](cluster-risk.md).

- **Against usable capacity, not total.** Usable = Total − HA − Buffer. The capacity kept for a host failure and the buffer of the policy are not available to VMs.
- **Cluster-wide, not the worst host.** Every sub-metric adds up the hosts of the cluster. A big host counts more than a small one. [Cluster Risk](cluster-risk.md) is the opposite: it takes the worst host.
- **Saturation is not contention.** Ballooned, swapped and zipped memory do not mean anything is slow yet. They are real consumption, so they have their own sub-metrics.

All 6 metrics are published on the cluster object under `vCommunity|Cluster Consumption`. The KPI itself is `vCommunity|Cluster Consumption|Cluster Consumption Score`.

It is one of the three inputs of the [Periodic Cluster Check](periodic-cluster-check.md). Where it fits in the capacity model: [Capacity Management Model](../../concepts/capacity-management.md).

Code: [`Management Pack/app/metrics/cluster/cluster_consumption_metrics.py`](../../../Management%20Pack/app/metrics/cluster/cluster_consumption_metrics.py)

Source of the limits: [`formula/cluster-consumption.png`](formula/cluster-consumption.png)

## Known limitations

> **Read this before using the metrics.**

- **Memory Tiering Consumption is not yet confirmed on a live system.** The lab has a host with an NVMe tier but no value for its usage, so the stat and its unit (MB) are taken from the VCF Operations definition.
- **Usable Capacity 0 has two situations, with different results:**
  - **Hosts run, but HA and the Buffer leave nothing to VMs.** VCF Operations reports Usable Capacity 0. Seen on a live system: HA tolerating one host failure, with one of two hosts running. The VMs on that host still consume, so Cluster Consumption is 100 (fully consumed). The rows of that resource are not published: there is no meaningful % of 0.
  - **No host runs:** all are down, powered off, in maintenance mode or disconnected. No VM runs, so nothing is consumed, and Cluster Consumption is not 100. The rows and the KPI have no data.
- **Usable capacity not reported is no data.** Then CPU and memory have no value for that cycle, and are left out of the KPI. They are never scored against the total instead.
- **A worse sub-metric can lower Cluster Consumption.** When a sub-metric crosses into the next tier, its weight doubles. If it is still less consumed than the sub-metrics already driving Cluster Consumption, the KPI goes down. See [A worse sub-metric can lower Cluster Risk](cluster-risk.md#known-limitation-a-worse-sub-metric-can-lower-cluster-risk), which uses the same scoring.
- **CPU Usable Capacity in threads comes from a ratio in MHz.** VCF Operations reports CPU Usable Capacity in MHz, not in threads. The pack divides it by the CPU Total Capacity, also in MHz, and applies that percentage to the threads of the running hosts. No step converts MHz to threads. This is exact only when every host has the same clock speed and the same hyper-threading setting. Example: host A has 32 cores with hyper-threading (64 threads), host B the same 32 cores without it (32 threads), so each is half of the cluster's MHz. If HA and the buffer remove 50 % of the MHz, the pack counts 96 × 50 % = 48 usable threads. But the threads actually left are 32 if host A fails, or 64 if host B fails.
- **The memory percentage is applied to the NVMe memory tier too.** Memory Usable Capacity is reported for DRAM. The same percentage is applied to the NVMe tier, which assumes HA and the buffer remove the same part of each.
- **Total Capacity and Usable Capacity.** Total Capacity is every host in the cluster, whatever its state: it changes only when a host is added or removed. Usable Capacity counts only the hosts that can run VMs: a host in maintenance mode, disconnected, powered off or in standby stays in Total Capacity but adds nothing to Usable Capacity. So Usable Capacity changes with the state of the hosts, and can be 0 if all hosts are down, powered off, in maintenance mode or disconnected.
- **To be validated: does VCF Operations count a host that is down in its Total Capacity?** The pack takes VCF Operations' Usable Capacity as a percentage of its Total Capacity (`cpu|capacity_provisioned`, `mem|host_provisioned`), then applies that percentage to the hosts that can run VMs. If VCF Operations keeps a host in maintenance mode in its Total but not in its Usable Capacity, that host lowers the percentage **and** is left out of the hosts it is applied to, so it reduces Usable Capacity twice. Not yet checked on a live system.

## The 5 sub-metrics and their limits

Every sub-metric is "lower is better", in % of the usable capacity.

| Group | Sub-metric | Green ends at | Yellow ends at | Orange ends at | Score hits 0 at |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Utilization | Cluster-wide ESXi CPU Thread Utilization | 55 | 70 | 85 | 100 |
| Utilization | Cluster-wide ESXi Memory Consumed | 70 | 80 | 90 | 100 |
| Saturation | Cluster Memory Tiering Consumption | 4 | 8 | 16 | 32 |
| Saturation | Cluster-wide ESXi Memory Ballooned | 1 | 2 | 4 | 8 |
| Saturation | Cluster-wide ESXi Memory Zip Swap (swapped + compressed) | 0.25 | 0.5 | 1 | 2 |

The score is 100 at 0 for every row. No green range is excluded: every row with data counts in the KPI.

## How each sub-metric is calculated

### Usable Capacity

**Usable Capacity = Total Capacity − HA − Buffer.** VCF Operations calculates it for each cluster, from its HA admission control and the **Capacity Buffer (Demand)** set in the policy (**Capacity Settings** of Cluster Compute Resource). It reports it in MHz for CPU and in KB for memory. The sub-metrics need it in threads, in GB of DRAM and in GB of NVMe tier, so the pack takes Usable Capacity as a percentage of Total Capacity, and applies that percentage to what the running hosts have:

| Usable Capacity | Percentage, read from VCF Operations | Applied to |
| :--- | :--- | :--- |
| CPU, in threads | `cpu\|demand\|usableCapacity` ÷ `cpu\|capacity_provisioned`, both in MHz | The threads of the running hosts |
| Memory, in DRAM | `mem\|demand\|usableCapacity` ÷ `mem\|host_provisioned`, both in KB | The DRAM of the running hosts |
| Memory, in NVMe tier | The memory percentage above | The NVMe tier of the running hosts |

The MHz values are used only for the percentage: no step converts MHz to threads. That is exact only when all hosts are the same. See [Known limitations](#known-limitations).

**CPU Usable Capacity is in threads, not MHz.** This differs from VCF Operations on purpose. Capacity is about quantity, not quality: how many VMs fit (space), not how fast they run (speed). MHz measures speed, so a cluster's CPU capacity is counted in threads.

Each Usable Capacity is calculated once per cluster, and every row of that resource divides by the same one. The hosts it counts are the running hosts that report the resource: CPU utilization for CPU, DRAM and consumed memory for DRAM, and a tier for the NVMe tier. A row adds up its own stat over those same hosts. If one of them does not report it, the row has no data that cycle, rather than a sum that misses a host.

Example: HA and the buffer take 20 % of a cluster, so Usable Capacity is 80 % of Total Capacity, and a host with 512 GB of DRAM counts as 409.6 GB of usable DRAM. DRAM and the NVMe memory tier are kept apart: each memory row uses only one of them.

### The sub-metrics

The hosts that count are the running hosts with data. A host is left out when it cannot run VMs, or when nothing current is known about it, so its idle capacity does not make the cluster look emptier than it is:

| Host state | Why it is left out |
| :--- | :--- |
| Not responding | Dead, or cut off from vCenter. vSphere HA restarts its VMs elsewhere. |
| Disconnected | Nothing current is known about it or its VMs. |
| Powered off, or in standby (DPM) | Runs no VM. |
| In maintenance mode | vSphere allows no running VM on a host in maintenance mode. A host still *entering* maintenance mode counts as running, because its VMs are still on it. |
| No current value | No value for the stat in the last 10 minutes. See [No stale values](README.md#no-stale-values). |

A host that is left out stays in Total Capacity, but adds nothing to Usable Capacity.

| Sub-metric | Cluster-wide | Source |
| :--- | :--- | :--- |
| CPU Thread Utilization | CPU threads in use on all hosts ÷ CPU Usable Capacity in threads. Threads in use = `cpu.utilization` % × threads, per host. | Host stat `cpu\|utilization_average`. Threads: see [Cluster Risk](cluster-risk.md#where-each-hosts-data-comes-from). |
| Memory Consumed | Consumed memory of all hosts ÷ Memory Usable Capacity in DRAM | Host stats `mem\|consumed_average`, `MEM_DRAM_CAPACITY` |
| Memory Tiering Consumption | NVMe tier in use on all hosts ÷ Memory Usable Capacity in NVMe tier. Hosts without a tier are left out; a cluster without any has no value. | Host stats `mem:NVMe\|tier.usage` (MB), `mem:NVMe\|memory_tier_size` (KB) |
| Memory Ballooned | Ballooned memory of all hosts ÷ Memory Usable Capacity in DRAM | Host stat `mem\|vmmemctl_average` |
| Memory Zip Swap | Compressed plus swapped memory of all hosts ÷ Memory Usable Capacity in DRAM | Host stats `mem\|compressed_average`, `mem\|swapout_average` |

`MEM_DRAM_CAPACITY` is the host's DRAM only, never DRAM plus a memory tier. See [Host memory capacity](cluster-risk.md#host-memory-capacity-mem_dram_capacity).

**Two extra requests per cycle.** The CPU, DRAM and memory host stats are the ones Cluster Risk already reads in the same cycle. The usable capacity of all clusters, and the NVMe tier of all hosts, are read in one request each.

## How the score is calculated

The same way as every KPI, then flipped like Cluster Risk:

1. Each sub-metric value gets a score from 100 to 0, depending on the tier it is in.
2. The scores are combined in a weighted average, where 100 is best. A sub-metric in the red tier weighs 8×, orange 4×, yellow 2×, green 1×.
3. **Cluster Consumption = 100 − that weighted average**, so that higher means more consumed.

Its bands are therefore those of Cluster Risk: green 0–25, yellow 25–50, orange 50–75, **red 75–100**. See [Bands: red is high](cluster-risk.md#bands-red-is-high).

## Worked example

Two hosts: a big one with 32 cores (64 threads) and 512 GB of DRAM, and a small one with 16 cores (32 threads) and 256 GB. HA and the buffer take 20 % of the cluster, so Usable Capacity is 80 % of Total Capacity, for CPU and for memory.

| | CPU Thread Utilization | Consumed | Ballooned |
| :--- | :--- | :--- | :--- |
| Big host | 40 % | 256 GB | 5.12 GB |
| Small host | 70 % | 230.4 GB | 0 |
| **Of the total** | `48 of 96 threads` = 50 % | `486.4 of 768 GB` = 63.33 % | `5.12 of 768 GB` = 0.67 % |
| **Of the usable** | `48 of 76.8 threads` = **62.5 %** | `486.4 of 614.4 GB` = **79.17 %** | `5.12 of 614.4 GB` = **0.83 %** |

The average of 40 % and 70 % would be 55 %. Cluster-wide is 50 % of the total, because the big host has twice the threads, and 62.5 % of what VMs may use.

- No memory tiering, so Memory Tiering Consumption is left out. Zip Swap is 0.
- Scores: CPU yellow `75 − (62.5 − 55) / 15 × 25` = 62.5, weight 2. Memory yellow `75 − (79.17 − 70) / 10 × 25` = 52.08, weight 2. Ballooned green `100 − 0.83 × 25` = 79.25, weight 1. Zip Swap 100, weight 1.
- Weighted average = `(62.5 × 2 + 52.08 × 2 + 79.25 + 100) / 6` = 68.07. Cluster Consumption = `100 − 68.07` = **31.93**.

The same example is checked by the tests in [`Management Pack/tests/test_cluster_consumption_metrics.py`](../../../Management%20Pack/tests/test_cluster_consumption_metrics.py).

## Missing data

A sub-metric with no data is not published for that cycle, and it is left out of the KPI. It is never counted as 0, because a value of 0 means "nothing consumed".

- Without usable capacity for CPU or memory, those rows have no value. The log says which stat was missing.
- If the host stats request of Cluster Risk fails, only Memory Tiering Consumption can have a value.
- A host that VCF Operations does not know is left out.
