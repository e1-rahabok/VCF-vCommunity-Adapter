# Cluster Risk KPI

**Cluster Risk** is a 0 to 100 % value for a vSphere cluster. **Higher is worse: 0 is no risk, 100 is the highest risk.** Cluster Consumption works the same way. The other KPIs are higher-is-better.

Cluster Risk is a leading indicator. It shows how close the cluster is to contention, before the VMs feel it, and covers both capacity and performance. [Cluster Performance](cluster-performance.md) shows the contention that is happening now.

Every sub-metric takes the highest or worst ESXi host in the cluster, because one full host can hurt its VMs while the cluster average still looks fine.

Host memory means DRAM only. Every memory percentage and ratio is measured against the host's DRAM, called `MEM_DRAM_CAPACITY`. A memory tier such as NVMe is never added. See [Host memory capacity](#host-memory-capacity-mem_dram_capacity).

The KPI and its 12 sub-metrics are published on the cluster object under `vCommunity|Cluster Risk`. The KPI is `vCommunity|Cluster Risk|Cluster Risk Score`.

Code: [`Management Pack/app/metrics/cluster/cluster_risk_metrics.py`](../../../Management%20Pack/app/metrics/cluster/cluster_risk_metrics.py)

Source of the limits: [`formula/cluster-risk.png`](formula/cluster-risk.png)

## Thresholds

Every sub-metric is lower-is-better.

| Group | Sub-metric | Unit | Green ends at | Yellow ends at | Orange ends at | Score hits 0 at |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Utilization | Highest ESXi CPU Thread Utilization | % | Excluded (below 60) | 80 | 90 | 95 |
| Utilization | Worst ESXi CPU Imbalance | ratio | 1 (exactly) | 1.3 | 1.6 | 2 |
| Utilization | Highest ESXi Memory Consumed | % | Excluded (below 80) | 90 | 95 | 100 |
| Saturation | Worst ESXi Memory Ballooned | % | 1 | 2 | 4 | 8 |
| Saturation | Worst ESXi Memory Zip Swap (swapped + compressed) | % | 0.25 | 0.5 | 1 | 2 |
| Saturation | Worst ESXi Memory Tiering Latency | µs | 150 | 300 | 450 | 600 |
| Reservation | Highest ESXi CPU Reservation | % | Excluded (below 10) | 40 | 60 | 80 |
| Reservation | Highest ESXi Memory Reservation | % | Excluded (below 10) | 40 | 60 | 80 |
| Allocation | Highest ESXi CPU Overcommit Ratio | ratio | Excluded (below 1) | 2 | 3 | 4 |
| Allocation | Highest ESXi Memory Overcommit Ratio | ratio | Excluded (below 1) | 1.4 | 1.8 | 2.2 |
| Monster VM | Highest CPU Monster VM to Host Ratio | ratio | 1 | 2 | 3 | 4 |
| Monster VM | Highest Memory Monster VM to Host Ratio | ratio | 1 | 2 | 3 | 4 |

Every row scores 100 at 0, except CPU Imbalance, which scores 100 at 1: one running thread per running core. Any imbalance above 1 is yellow.

**Excluded.** The source table marks six green ranges as "Excluded". A host that is not busy, has little reserved or is not overcommitted tells you nothing about risk. While these sub-metrics are green, they are left out of the KPI instead of scoring 100. They count once they leave green.

## How each sub-metric is calculated

Each sub-metric is calculated per host, and the highest (worst) host is kept.

| Sub-metric | Per host | Source |
| :--- | :--- | :--- |
| CPU Thread Utilization | `cpu.utilization`: the % of the host's CPU threads in use, hyper-threading aware | VCF Operations: `cpu\|utilization_average` |
| CPU Imbalance | Running CPU threads ÷ running CPU cores. Running threads = `cpu.utilization` % × threads. Running cores = `cpu.coreUtilization` % × cores. | VCF Operations: `cpu\|utilization_average`, `cpu\|coreUtilization_average`, `hardware\|cpuInfo\|numCpuCores`. Threads: see below. |
| Memory Consumed | Consumed memory, as a % of host DRAM | VCF Operations: `mem\|consumed_average` / `MEM_DRAM_CAPACITY` |
| Memory Ballooned | Ballooned memory, as a % of host DRAM | VCF Operations: `mem\|vmmemctl_average` / `MEM_DRAM_CAPACITY` |
| Memory Zip Swap | Compressed plus swapped memory, as a % of host DRAM | VCF Operations: (`mem\|compressed_average` + `mem\|swapout_average`) / `MEM_DRAM_CAPACITY` |
| Memory Tiering Latency | Read latency of the NVMe memory tier. Only hosts with memory tiering have it; other hosts are left out of this row. | VCF Operations: `mem:NVMe\|latency.read_latest` (µs) |
| CPU Reservation | Reserved CPU, as a % of host CPU capacity | VCF Operations: `cpu\|reservedCapacity_average` / `cpu\|totalCapacity_average` |
| Memory Reservation | Reserved memory, as a % of host DRAM | VCF Operations: `mem\|reservedCapacity_average` / `MEM_DRAM_CAPACITY` |
| CPU Overcommit Ratio | vCPUs of the powered-on VMs, per physical core | VCF Operations: `cpu\|vcpus_allocated_on_all_powered_on_vms`, `hardware\|cpuInfo\|numCpuCores` |
| Memory Overcommit Ratio | Memory of the powered-on VMs ÷ host DRAM. Both are in KB. | VCF Operations: `mem\|memory_allocated_on_all_powered_on_vms` / `MEM_DRAM_CAPACITY` |
| CPU Monster VM to Host Ratio | vCPUs of the largest powered-on VM, against the monster size of its host (see below) | VCF Operations: VM `config\|hardware\|numCpu`, host `hardware\|cpuInfo\|numCpuCores` |
| Memory Monster VM to Host Ratio | Memory of the largest powered-on VM, against the monster size of its host (see below) | VCF Operations: VM `config\|hardware\|memoryKB`. Host: `MEM_DRAM_CAPACITY`. |

### Where each host's data comes from

All data comes from VCF Operations. Nothing is read from vCenter. The host and VM properties are read once per collection cycle for all clusters. The host stats are read with one request per cluster, and Cluster Consumption reuses them.

| Data | VCF Operations source |
| :--- | :--- |
| Hosts of the cluster | Host property `summary\|parentCluster`, matched to the cluster name |
| Powered-on VMs of a host | VM properties `summary\|parentHost`, matched to the host name, and `summary\|runtime\|powerState` = "Powered On" |
| Physical cores | Host property `hardware\|cpuInfo\|numCpuCores` |
| Threads | 2 × cores when both `config\|hyperThread\|available` and `config\|hyperThread\|active` are "true". Otherwise the cores. |
| VM size | VM properties `config\|hardware\|numCpu` and `config\|hardware\|memoryKB` |
| Host memory (`MEM_DRAM_CAPACITY`) | Host stat `mem:DRAM\|memory_tier_total_capacity`. Fallback: `mem\|host_provisioned`. See below. |

Placement is by name, because `summary|parentCluster` and `summary|parentHost` hold the name shown in vCenter rather than an ID. Names are unique only inside one datacenter, so two clusters with the same name in different datacenters of one vCenter can be mixed up.

### Host memory capacity (MEM_DRAM_CAPACITY)

`MEM_DRAM_CAPACITY` is the host's DRAM, in KB. It is the denominator of Memory Consumed, Ballooned, Zip Swap, Memory Reservation and Memory Overcommit, and the base of the Memory Monster VM size.

| Order | VCF Operations stat | Used when |
| :--- | :--- | :--- |
| 1 | `mem:DRAM\|memory_tier_total_capacity` | It returns a value. This is the DRAM tier. |
| 2 | `mem\|host_provisioned` | The first returns nothing or 0. Also in KB. |

- If both return nothing, the memory rows of that host are left out. They are never scored against a guess.
- The expanded capacity (DRAM + NVMe) is never used. VMs run in DRAM, and NVMe holds only cold pages, so a % of DRAM + NVMe would understate the real pressure.

### When a VM is a monster

The Monster VM ratios compare the largest VM on a host with the size at which a VM becomes a monster on that host. A ratio of 1 means the largest VM is exactly that size. Above 1, it is a monster.

| | A VM is a monster when it has (defaults) | Example |
| :--- | :--- | :--- |
| CPU | More than 50 % of the host's physical cores. Cores, not threads. | A host with 64 cores and 128 threads: more than 32 vCPUs. |
| Memory | More than 40 % of the host's DRAM (`MEM_DRAM_CAPACITY`), or 256 GB, whichever is smaller. A memory tier such as NVMe does not count. | A host with 768 GB of DRAM and 768 GB of NVMe: 40 % is 307 GB, so the limit is 256 GB. |

The three numbers are settings under **Advanced Settings** of the [Adapter Instance](../../configuration-guide/adapter-instance.md#2-advanced-settings-optional):

| Setting | Default | Allowed |
| :--- | :--- | :--- |
| **Monster VM CPU (% of host cores)** | 50 | 1 to 100 |
| **Monster VM Memory (% of host DRAM)** | 40 | 1 to 100 |
| **Monster VM Memory Minimum (GB)** | 256 | 1 or more |

- An empty setting uses the default.
- A value that is not a whole number in the allowed range uses the default, and the adapter log has a warning.
- A change applies from the next collection cycle. Values already published are not recalculated.
- The limits of the ratio (green up to 1, then 2, 3 and 4) do not change, because 1 always means "exactly the monster size".

The worked examples below use the defaults.

## How the score is calculated

Each sub-metric is scored and combined like every KPI, see [How the pack scores a KPI](../../concepts/kpi-scoring-models.md#how-the-pack-scores-a-kpi). The weighted average has 100 as best, and the published value is flipped:

**Cluster Risk = 100 − the weighted average**, so that a higher value means more risk.

The scoring examples are in [Cluster Performance KPI](cluster-performance.md#worked-examples). The code is [`kpi_score.py`](../../../Management%20Pack/app/metrics/kpi_score.py).

### Bands: red is high

Because Cluster Risk is published as `100 − weighted average`, its bands mirror those of the higher-is-better KPIs:

| Band | Cluster Performance and other higher-is-better KPIs | Cluster Risk |
| :--- | :--- | :--- |
| Green | 75 – 100 | 0 – 25 |
| Yellow | 50 – 75 | 25 – 50 |
| Orange | 25 – 50 | 50 – 75 |
| Red | 0 – 25 | **75 – 100** |

- Only the published number is flipped. The sub-metrics, their limits, the weights, "Excluded" and missing data work exactly as for every KPI, in the same shared code. The flip is the last step, in `publish_kpi(..., higher_is_worse=True)`.
- The order and the distances between clusters are kept. A cluster whose weighted average is 10 points higher than another's has a Cluster Risk 10 points lower.
- Set thresholds the other way round. A symptom, alert or widget color range on `Cluster Risk Score` must treat high as bad: red from 75. The vSphere Cluster Capacity 2.0 dashboard uses the score with red from 75. The pack's other dashboards and reports use only the Risk sub-metrics.
- "Worst" means highest. vSphere World therefore uses the 90th percentile and the highest Cluster Risk, and the Periodic Cluster Check takes the high end of Cluster Risk and counts it red from 75.

## Worked examples

Two hosts, each with 32 cores (64 threads) and 512 GB of DRAM. Each runs four VMs of 4 vCPUs and 16 GB. The monster size on these hosts is 16 vCPUs (half of 32 cores) and 204.8 GB (40 % of 512 GB, less than 256 GB).

- **Low risk.** Both hosts at 40 % thread and 80 % core utilization (one running thread per running core), 50 % memory consumed, and nothing ballooned, swapped or reserved.
  - Left out: the six rows in their excluded green, and Memory Tiering Latency, because these hosts have no memory tiering.
  - Counted: CPU Imbalance 1 (100), Ballooned 0 (100), Zip Swap 0 (100), CPU Monster VM `4 / 16` = 0.25 (93.75), Memory Monster VM `16 / 204.8` = 0.08 (98).
  - 93.75 has weight 1.19 and 98 has weight 1.06. Weighted average = `(300 + 93.75 × 1.19 + 98 × 1.06) / (3 + 1.19 + 1.06)` = 98.18. Cluster Risk = `100 − 98.18` = **1.82**.
- **One busy host.** Host 1 at 90 % thread and 100 % core utilization. Host 2 at 30 % and 60 %.
  - CPU Thread Utilization 90 leaves its excluded green and lands at the start of red: 25 with weight 8.
  - CPU Imbalance of host 1 is `57.6 running threads / 32 running cores` = 1.8. Host 2 is 1.0. The worst, 1.8, is halfway through red: 12.5 with weight 11.31.
  - Weighted average = `(25 × 8 + 12.5 × 11.31 + 100 + 100 + 93.75 × 1.19 + 98 × 1.06) / (8 + 11.31 + 1 + 1 + 1.19 + 1.06)` = 32.11. Cluster Risk = `100 − 32.11` = **67.89**.

The tests in [`Management Pack/tests/test_cluster_risk_metrics.py`](../../../Management%20Pack/tests/test_cluster_risk_metrics.py) check the same examples.

## Known limitation: a worse sub-metric can lower Cluster Risk

> **Read this before you use a change in Cluster Risk to make a decision.**

A sub-metric that gets worse can make Cluster Risk go **down**. This happens when that sub-metric is still less bad than the sub-metrics already driving Cluster Risk, because its weight grows as it gets worse.

### Why

Cluster Risk is 100 minus a weighted average. When a sub-metric gets worse, its weight `2^((100 − score) / 25)` rises, so it counts more, and the weighted average moves toward that sub-metric's score. If that score is above the current weighted average, the average goes up and Cluster Risk goes down.

Two things raise a weight:

| Case | Weight | Example |
| :--- | :--- | :--- |
| A sub-metric gets worse | Rises smoothly with the score: 1.32 at 90, 1.74 at 80, 2.30 at 70 | Ballooned goes from a score of 90 to 80 |
| An "Excluded" sub-metric leaves green and is counted for the first time | From 0 to 2. The source table gives no value between "excluded" and yellow, so this is a step. | CPU Overcommit Ratio passes 1 after new VMs are deployed |

The rule: Cluster Risk goes down when the sub-metric's own level, `100 − its score`, is below the current Cluster Risk. So it happens only when Cluster Risk is already high because of worse sub-metrics. When the other sub-metrics are green, a sub-metric that gets worse always raises Cluster Risk.

### Example with 5 sub-metrics

Sub-metric A is red. B gets worse, from a score of 90 to 80. C, D and E stay at 90. All five are counted.

| Sub-metric | Before: score × weight | After: score × weight |
| :--- | :--- | :--- |
| A, red | 10 × 12.13 = 121.3 | 10 × 12.13 = 121.3 |
| **B, green** | **90 × 1.32 = 118.8** | **80 × 1.74 = 139.2** |
| C, D, E, green | 90 × 1.32 = 118.8 each | 90 × 1.32 = 118.8 each |
| Weighted average | 596.5 / 17.41 = 34.26 | 616.9 / 17.83 = 34.60 |
| **Cluster Risk** | **65.74** | **65.40** |

B got worse, but its score of 80 is still above the average of 34.26, which A holds down. Its weight rises from 1.32 to 1.74, so it pulls the average up, and Cluster Risk falls by 0.34. Once B's score drops below about 56, the weighted average falls and Cluster Risk rises again.

### Example: deploying VMs

Take the cluster from [One busy host](#worked-examples), at Cluster Risk 67.89. New idle VMs raise the CPU Overcommit Ratio of the hosts. Every other sub-metric stays the same. Values are rounded to two decimals before they are scored.

| CPU Overcommit Ratio | Tier | Score × weight | Cluster Risk |
| :--- | :--- | :--- | :--- |
| 0.5 | Excluded green | left out | 67.89 |
| 1.125, published as 1.12 (ten 4-vCPU VMs, five per host) | yellow | 72.00 × 2.17 | **64.52** |
| 1.5 | yellow | 62.50 × 2.83 | **64.63** |
| 2.5 | orange | 37.50 × 5.66 | **66.85** |
| 2.8 | orange | 30.00 × 6.96 | 68.37 |
| 3.5 | red | 12.50 × 11.31 | 74.25 |

From 1.125 to 2.5 the overcommit ratio rises, but Cluster Risk stays below 67.89. Only from about 2.7 is the sub-metric bad enough to raise Cluster Risk above its starting value.

### What it affects

- **Close for Business.** The [Periodic Cluster Check](periodic-cluster-check.md) reads Cluster Risk from its orange closure level, above 60. A cluster just above 60 can drop below it after VMs are deployed, and open again.
- **Trends.** A falling Cluster Risk does not always mean less risk. Check the sub-metrics.
- **Every KPI.** All KPIs use this scoring. [Cluster Consumption](cluster-consumption.md) has only the smooth case, because it has no Excluded sub-metrics. In the higher-is-better KPIs, such as [Cluster Performance](cluster-performance.md), a worse sub-metric can raise the score.

## Missing data

A sub-metric with no data is not published for that cycle, and it is left out of the KPI. It is never counted as 0, because 0 means no risk.

A stat whose latest value is more than 10 minutes old counts as no data. See [No stale values](README.md#no-stale-values).

- If the host stats request fails, only CPU Monster VM to Host Ratio is scored, because it needs only properties. Memory Monster VM needs the DRAM stat.
- A host that VCF Operations does not know is left out.
- Overcommit and Monster VM count powered-on VMs only.

## Source stats and units

These stats and units were checked on VCF Operations 9.1.1: `cpu|utilization_average` (vCenter `cpu.utilization`), `cpu|coreUtilization_average` (vCenter `cpu.coreUtilization`), `cpu|reservedCapacity_average` (MHz), `mem|reservedCapacity_average` (KB), `mem|swapout_average`, `mem:DRAM|memory_tier_total_capacity` (KB), `mem|host_provisioned` (KB) and `mem:NVMe|latency.read_latest` (µs).

- The properties endpoint, `POST api/resources/properties/latest/query`, returns a text property under `values` and a number under `data`. The code reads both.
- The latest stats endpoint, `POST api/resources/stats/latest/query`, also returns every instance of a stat it is asked for, such as `cpu:26|utilization_average` for CPU thread 26. The code keeps only the keys it asked for.
- Both responses are kept as test data in `tests/test_ops_inventory.py`.

`net|packetsRx_summation_sum` and `net|packetsTx_summation_sum`, used by Bad Network Packets, are deactivated by default. See [Policy](../../configuration-guide/policy.md).
