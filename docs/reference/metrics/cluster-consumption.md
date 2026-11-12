# Cluster Consumption KPI

**Cluster Consumption** is a 0 to 100 % value for a vSphere cluster. It measures the utilization and saturation of the cluster as a whole, against its usable capacity. **Higher is worse: 0 is nothing consumed, 100 is fully consumed**, the same direction as [Cluster Risk](cluster-risk.md).

- It is measured against usable capacity: Total − HA − Buffer. The capacity kept for a host failure and the buffer set in the policy are not available to VMs.
- It is cluster-wide. Every sub-metric adds up the hosts of the cluster, so a big host counts more than a small one. [Cluster Risk](cluster-risk.md) takes the worst host instead.
- Ballooned, swapped and compressed memory do not mean that VMs are slow yet, but they are real consumption, so they have their own sub-metrics.

The KPI and its 5 sub-metrics are published on the cluster object under `vCommunity|Cluster Consumption`. The KPI is `vCommunity|Cluster Consumption|Cluster Consumption Score`.

It is one of the three inputs of the [Periodic Cluster Check](periodic-cluster-check.md). For where it fits in the capacity model, see [Capacity Management Model](../../concepts/capacity-management.md).

Code: [`Management Pack/app/metrics/cluster/cluster_consumption_metrics.py`](../../../Management%20Pack/app/metrics/cluster/cluster_consumption_metrics.py)

Source of the limits: [`formula/cluster-consumption.png`](formula/cluster-consumption.png)

## Known limitations

> **Read this before you use the metrics.**

- **Memory Tiering Consumption has not been checked against a live value.** The stat and its unit (MB) come from the VCF Operations metric definition.
- **Usable Capacity 0 has two cases, with different results.**
  - Hosts run, but HA and the buffer leave nothing for VMs, so VCF Operations reports Usable Capacity 0. This happens, for example, when HA tolerates one host failure and only one of two hosts runs. The VMs on the running host still consume capacity, so Cluster Consumption is 100. The sub-metrics of that resource are not published, because a % of 0 has no meaning.
  - No host runs: all are down, powered off, in maintenance mode or disconnected. No VM runs and nothing is consumed, so the sub-metrics and the KPI have no data.
- **No reported usable capacity means no data.** CPU and memory then have no value for that cycle and are left out of the KPI. They are never scored against the total capacity instead.
- **A worse sub-metric can lower Cluster Consumption.** A sub-metric's weight rises as it gets worse. If it is still less consumed than the sub-metrics already driving the KPI, the KPI goes down. See [A worse sub-metric can lower Cluster Risk](cluster-risk.md#known-limitation-a-worse-sub-metric-can-lower-cluster-risk), which uses the same scoring.
- **CPU usable threads come from a ratio in MHz.** VCF Operations reports CPU Usable Capacity in MHz. The pack divides it by CPU Total Capacity, also in MHz, and applies that percentage to the threads of the running hosts. This is exact only when every host has the same clock speed and the same hyper-threading setting. Example: host A has 32 cores with hyper-threading (64 threads), and host B has 32 cores without it (32 threads), so each has half of the cluster's MHz. If HA and the buffer take 50 % of the MHz, the pack counts 96 × 50 % = 48 usable threads. The threads actually left are 32 if host A fails, or 64 if host B fails.
- **The memory percentage is also applied to the NVMe memory tier.** VCF Operations reports Memory Usable Capacity for DRAM. Applying the same percentage to the NVMe tier assumes that HA and the buffer take the same share of each.
- **Total Capacity and Usable Capacity count hosts differently.** Total Capacity covers every host in the cluster, whatever its state, and changes only when a host is added or removed. Usable Capacity counts only the hosts that can run VMs. A host in maintenance mode, disconnected, powered off or in standby stays in Total Capacity but adds nothing to Usable Capacity.
- **Open question: does VCF Operations keep a host that is down in its Total Capacity?** The pack takes VCF Operations' Usable Capacity as a percentage of its Total Capacity (`cpu|capacity_provisioned`, `mem|host_provisioned`), then applies that percentage to the hosts that can run VMs. If VCF Operations keeps a host in maintenance mode in Total but not in Usable Capacity, that host lowers the percentage and is also left out of the hosts it is applied to, so it reduces usable capacity twice. This has not been checked on a live system.

## The 5 sub-metrics and their limits

Every sub-metric is lower-is-better, in % of the usable capacity.

| Group | Sub-metric | Green ends at | Yellow ends at | Orange ends at | Score hits 0 at |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Utilization | Cluster-wide ESXi CPU Thread Utilization | 55 | 70 | 85 | 100 |
| Utilization | Cluster-wide ESXi Memory Consumed | 70 | 80 | 90 | 100 |
| Saturation | Cluster Memory Tiering Consumption | 4 | 8 | 16 | 32 |
| Saturation | Cluster-wide ESXi Memory Ballooned | 1 | 2 | 4 | 8 |
| Saturation | Cluster-wide ESXi Memory Zip Swap (swapped + compressed) | 0.25 | 0.5 | 1 | 2 |

Every row scores 100 at 0. No green range is excluded, so every row with data counts in the KPI.

## How each sub-metric is calculated

### Usable Capacity

**Usable Capacity = Total Capacity − HA − Buffer.** VCF Operations calculates it for each cluster from its HA admission control and the **Capacity Buffer (Demand)** in the policy (**Capacity Settings** of Cluster Compute Resource). It reports CPU in MHz and memory in KB. The sub-metrics need threads, GB of DRAM and GB of NVMe tier, so the pack takes Usable Capacity as a percentage of Total Capacity and applies that percentage to what the running hosts have:

| Usable Capacity | Percentage, read from VCF Operations | Applied to |
| :--- | :--- | :--- |
| CPU, in threads | `cpu\|demand\|usableCapacity` ÷ `cpu\|capacity_provisioned`, both in MHz | The threads of the running hosts |
| Memory, in DRAM | `mem\|demand\|usableCapacity` ÷ `mem\|host_provisioned`, both in KB | The DRAM of the running hosts |
| Memory, in NVMe tier | The memory percentage above | The NVMe tier of the running hosts |

The MHz values are used only for the percentage. No step converts MHz to threads, so the result is exact only when all hosts are alike. See [Known limitations](#known-limitations).

The pack counts CPU capacity in threads rather than MHz, unlike VCF Operations. Capacity here is about how many VMs fit, not how fast they run, and MHz measures speed.

Each Usable Capacity is calculated once per cluster, and every row of that resource divides by it. It counts the running hosts that report the resource: CPU utilization for CPU, DRAM and consumed memory for DRAM, and a tier for the NVMe tier. A row adds up its own stat over the same hosts. If one of them does not report the stat, the row has no data for that cycle rather than a sum that misses a host.

Example: HA and the buffer take 20 % of a cluster, so Usable Capacity is 80 % of Total Capacity, and a host with 512 GB of DRAM counts as 409.6 GB of usable DRAM. DRAM and the NVMe tier are kept apart: each memory row uses only one of them.

### The sub-metrics

Only running hosts with data count. A host is left out when it cannot run VMs, or when nothing current is known about it, so that its idle capacity does not make the cluster look emptier than it is:

| Host state | Why it is left out |
| :--- | :--- |
| Not responding | It is down or cut off from vCenter. vSphere HA restarts its VMs elsewhere. |
| Disconnected | Nothing current is known about it or its VMs. |
| Powered off, or in standby (DPM) | It runs no VMs. |
| In maintenance mode | vSphere runs no VMs on a host in maintenance mode. A host still entering maintenance mode counts as running, because its VMs are still on it. |
| No current value | It has no value for the stat in the last 10 minutes. See [No stale values](README.md#no-stale-values). |

A host that is left out stays in Total Capacity but adds nothing to Usable Capacity.

| Sub-metric | Cluster-wide | Source |
| :--- | :--- | :--- |
| CPU Thread Utilization | CPU threads in use on all hosts ÷ CPU Usable Capacity in threads. Threads in use = `cpu.utilization` % × threads, per host. | Host stat `cpu\|utilization_average`. Threads: see [Cluster Risk](cluster-risk.md#where-each-hosts-data-comes-from). |
| Memory Consumed | Consumed memory of all hosts ÷ Memory Usable Capacity in DRAM | Host stats `mem\|consumed_average`, `MEM_DRAM_CAPACITY` |
| Memory Tiering Consumption | NVMe tier in use on all hosts ÷ Memory Usable Capacity in NVMe tier. Hosts without a tier are left out. A cluster without any has no value. | Host stats `mem:NVMe\|tier.usage` (MB), `mem:NVMe\|memory_tier_size` (KB) |
| Memory Ballooned | Ballooned memory of all hosts ÷ Memory Usable Capacity in DRAM | Host stat `mem\|vmmemctl_average` |
| Memory Zip Swap | Compressed plus swapped memory of all hosts ÷ Memory Usable Capacity in DRAM | Host stats `mem\|compressed_average`, `mem\|swapout_average` |

`MEM_DRAM_CAPACITY` is the host's DRAM only, never DRAM plus a memory tier. See [Host memory capacity](cluster-risk.md#host-memory-capacity-mem_dram_capacity).

Cluster Consumption reuses the host stats that Cluster Risk reads for the same cluster in the same cycle. It adds two requests per cycle: one for the usable capacity of all clusters, and one for the NVMe tier of all hosts.

## How the score is calculated

Each sub-metric is scored and combined like every KPI, see [How the pack scores a KPI](../../concepts/kpi-scoring-models.md#how-the-pack-scores-a-kpi). The weighted average has 100 as best, and the published value is flipped, as for Cluster Risk:

**Cluster Consumption = 100 − the weighted average**, so that a higher value means more consumed.

Its bands are those of Cluster Risk: green 0–25, yellow 25–50, orange 50–75, **red 75–100**. See [Bands: red is high](cluster-risk.md#bands-red-is-high).

## Worked example

Two hosts: a big one with 32 cores (64 threads) and 512 GB of DRAM, and a small one with 16 cores (32 threads) and 256 GB. HA and the buffer take 20 % of the cluster, so Usable Capacity is 80 % of Total Capacity for CPU and for memory.

| | CPU Thread Utilization | Consumed | Ballooned |
| :--- | :--- | :--- | :--- |
| Big host | 40 % | 256 GB | 5.12 GB |
| Small host | 70 % | 230.4 GB | 0 |
| **Of the total** | `48 of 96 threads` = 50 % | `486.4 of 768 GB` = 63.33 % | `5.12 of 768 GB` = 0.67 % |
| **Of the usable** | `48 of 76.8 threads` = **62.5 %** | `486.4 of 614.4 GB` = **79.17 %** | `5.12 of 614.4 GB` = **0.83 %** |

The plain average of 40 % and 70 % would be 55 %. Cluster-wide it is 50 % of the total, because the big host has twice the threads, and 62.5 % of what VMs may use.

- There is no memory tiering, so Memory Tiering Consumption is left out. Zip Swap is 0.
- Scores: CPU is yellow, `75 − (62.5 − 55) / 15 × 25` = 62.5, weight 2.83. Memory is yellow, `75 − (79.17 − 70) / 10 × 25` = 52.08, weight 3.78. Ballooned is green, `100 − 0.83 × 25` = 79.25, weight 1.78. Zip Swap is 100, weight 1.
- Weighted average = `(62.5 × 2.83 + 52.08 × 3.78 + 79.25 × 1.78 + 100) / (2.83 + 3.78 + 1.78 + 1)` = 65.47. Cluster Consumption = `100 − 65.47` = **34.53**.

The tests in [`Management Pack/tests/test_cluster_consumption_metrics.py`](../../../Management%20Pack/tests/test_cluster_consumption_metrics.py) check the same example.

## Missing data

A sub-metric with no data is not published for that cycle, and it is left out of the KPI. It is never counted as 0, because 0 means nothing consumed.

- Without usable capacity for CPU or memory, those rows have no value. The adapter log names the missing stat.
- If the host stats request fails, no host counts as running, so nothing is published for the cluster that cycle.
- A host that VCF Operations does not know is left out.
