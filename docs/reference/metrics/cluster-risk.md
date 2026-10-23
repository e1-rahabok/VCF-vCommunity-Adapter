# Cluster Risk KPI

**Cluster Risk** is a single 0-100 % value for a vSphere cluster. **Higher is worse: 0 means no risk, 100 means maximum risk.** It is the only KPI of this pack where higher is worse. It is a leading indicator: it warns before the VMs feel contention. It covers both capacity and performance.

- [Cluster Performance](cluster-performance.md) shows contention that is happening now.
- Cluster Risk shows how close the cluster is to it.

Every sub-metric takes the highest or worst ESXi host in the cluster. One full host can hurt its VMs while the cluster average still looks fine.

**Host memory is DRAM only.** Every memory share and ratio is measured against the host's DRAM (the DIMMs), called `MEM_DRAM_CAPACITY`. A memory tier such as NVMe is never added. There is no use case, in Risk or Performance, for comparing against the expanded capacity (DRAM + NVMe). See [Host memory capacity](#host-memory-capacity-mem_dram_capacity).

All 13 metrics are published on the cluster object under `vCommunity|Cluster Risk`. The KPI itself is `vCommunity|Cluster Risk|Cluster Risk Score`.

Code: [`Management Pack/app/metrics/cluster/cluster_risk_metrics.py`](../../../Management%20Pack/app/metrics/cluster/cluster_risk_metrics.py)

Source of the limits: [`formula/cluster-risk.png`](formula/cluster-risk.png)

## The 12 sub-metrics and their limits

Every sub-metric is "lower is better".

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

The score is 100 at 0 for every row, except CPU Imbalance, where it is 100 at 1 (one running thread per running core). Any imbalance is yellow.

**Excluded.** Six green ranges are marked "Excluded" in the source table. A host that is not busy, has little reserved or is not overcommitted says nothing about risk. So while they are green, these sub-metrics are left out of the KPI instead of scoring 100. They count once they leave green.

## How each sub-metric is calculated

Each sub-metric is calculated per host, then the highest (worst) host is kept.

| Sub-metric | Per host | Source |
| :--- | :--- | :--- |
| CPU Thread Utilization | `cpu.utilization`: the share of the host's CPU threads in use, hyper-threading aware | VCF Operations: `cpu\|utilization_average` |
| CPU Imbalance | Count of running CPU threads ÷ count of running CPU cores. Running threads = `cpu.utilization` % × threads. Running cores = `cpu.coreUtilization` % × cores. | VCF Operations: `cpu\|utilization_average`, `cpu\|coreUtilization_average`, `hardware\|cpuInfo\|numCpuCores`. Threads: see below. |
| Memory Consumed | Consumed memory, as a share of host DRAM | VCF Operations: `mem\|consumed_average` / `MEM_DRAM_CAPACITY` |
| Memory Ballooned | Ballooned memory, as a share of host DRAM | VCF Operations: `mem\|vmmemctl_average` / `MEM_DRAM_CAPACITY` |
| Memory Zip Swap | Compressed plus swapped memory, as a share of host DRAM | VCF Operations: (`mem\|compressed_average` + `mem\|swapout_average`) / `MEM_DRAM_CAPACITY` |
| Memory Tiering Latency | Read latency of the NVMe memory tier. Only hosts with memory tiering have it; for the others it is left out. | VCF Operations: `mem:NVMe\|latency.read_latest` (µs) |
| CPU Reservation | Reserved CPU, as a share of host CPU capacity | VCF Operations: `cpu\|reservedCapacity_average` / `cpu\|totalCapacity_average` |
| Memory Reservation | Reserved memory, as a share of host DRAM | VCF Operations: `mem\|reservedCapacity_average` / `MEM_DRAM_CAPACITY` |
| CPU Overcommit Ratio | vCPUs allocated to the powered-on VMs, per physical core | VCF Operations: `cpu\|vcpus_allocated_on_all_powered_on_vms`, `hardware\|cpuInfo\|numCpuCores` |
| Memory Overcommit Ratio | Memory allocated to the powered-on VMs, divided by host DRAM. Both are in KB, so they divide directly. | VCF Operations: `mem\|memory_allocated_on_all_powered_on_vms` / `MEM_DRAM_CAPACITY` |
| CPU Monster VM to Host Ratio | vCPUs of the largest powered-on VM, against the monster size of its host (see below) | VCF Operations: VM `config\|hardware\|numCpu`, host `hardware\|cpuInfo\|numCpuCores` |
| Memory Monster VM to Host Ratio | Memory of the largest powered-on VM, against the monster size of its host (see below) | VCF Operations: VM `config\|hardware\|memoryKB`. Host: `MEM_DRAM_CAPACITY`. |

### Where each host's data comes from

Everything comes from VCF Operations, read once per collection cycle for all objects, so nothing is collected twice. Nothing is read from vCenter.

| Data | VCF Operations source |
| :--- | :--- |
| Hosts of the cluster | Host property `summary\|parentCluster`, matched to the cluster name |
| Powered-on VMs of a host | VM properties `summary\|parentHost`, matched to the host name, and `summary\|runtime\|powerState` = "Powered On" |
| Physical cores | Host property `hardware\|cpuInfo\|numCpuCores` |
| Threads | 2 × cores when both `config\|hyperThread\|available` and `config\|hyperThread\|active` are "true". Otherwise the cores. |
| VM size | VM properties `config\|hardware\|numCpu` and `config\|hardware\|memoryKB` |
| Host memory (`MEM_DRAM_CAPACITY`) | Host stat `mem:DRAM\|memory_tier_total_capacity`. Fallback: `mem\|host_provisioned`. See below. |

Placement is by name, because `summary|parentCluster` and `summary|parentHost` hold the name shown in vCenter, not an id. Names are unique inside one datacenter, so do not mix datacenters in one adapter instance.

### Host memory capacity (MEM_DRAM_CAPACITY)

`MEM_DRAM_CAPACITY` is the host's DRAM, in KB. It is the denominator of Memory Consumed, Ballooned, Zip Swap, Memory Reservation and Memory Overcommit, and the base of the Memory Monster VM size.

| Order | VCF Operations stat | Used when |
| :--- | :--- | :--- |
| 1 | `mem:DRAM\|memory_tier_total_capacity` | It returns a value. This is the DRAM tier. |
| 2 | `mem\|host_provisioned` | The first returns nothing, or 0. Also in KB. |

- If both return nothing, the memory rows of that host are left out. They are never scored against a guess.
- The expanded capacity (DRAM + NVMe) is never used. VMs run in DRAM; NVMe only holds cold pages. A share of DRAM + NVMe would look smaller than the real pressure.

### When a VM is a monster

The Monster VM ratios compare the largest VM with the size at which a VM becomes a monster on its host. 1 means the largest VM is exactly that size. Above 1 it is a monster.

| | A VM is a monster when it has (defaults) | Example |
| :--- | :--- | :--- |
| CPU | More than 50 % of the host's physical cores. Cores, not threads. | A host with 64 cores and 128 threads: more than 32 vCPU. |
| Memory | More than 40 % of the host's DRAM (`MEM_DRAM_CAPACITY`), or 256 GB, whichever is smaller. A memory tier such as NVMe does not count. | A host with 768 GB of DRAM and 768 GB of NVMe: 40 % is 307 GB, so 256 GB. |

The three numbers are account settings, under **Advanced Settings** of the [adapter instance](../../configuration-guide/adapter-instance.md#2-advanced-settings-optional):

| Setting | Default | Allowed |
| :--- | :--- | :--- |
| **Monster VM CPU (% of host cores)** | 50 | 1 to 100 |
| **Monster VM Memory (% of host DRAM)** | 40 | 1 to 100 |
| **Monster VM Memory Minimum (GB)** | 256 | 1 or more |

An empty or invalid value uses the default and logs a warning. A change applies from the next collection cycle; values already published are not recalculated. The limits of the ratio (green to 1, then 2, 3, 4) do not change: 1 is always "exactly the monster size". The worked examples below use the defaults.

## How the score is calculated

The same way as every KPI:

1. Each sub-metric value gets a score from 100 to 0, depending on the tier it is in.
2. The scores are combined in a weighted average, where 100 is best. A sub-metric in the red tier weighs 8×, orange 4×, yellow 2×, green 1×.
3. **Cluster Risk = 100 − that weighted average**, so that higher means more risk.

The full explanation, with a worked example, is in [Cluster Performance KPI](cluster-performance.md#step-2-score-each-sub-metric). The code is [`kpi_score.py`](../../../Management%20Pack/app/metrics/kpi_score.py).

### Bands: red is high

Because Cluster Risk is published as `100 − weighted average`, its bands are the mirror of the other KPIs:

| Band | Other KPIs (Performance) | Cluster Risk |
| :--- | :--- | :--- |
| Green | 75 – 100 | 0 – 25 |
| Yellow | 50 – 75 | 25 – 50 |
| Orange | 25 – 50 | 50 – 75 |
| Red | 0 – 25 | **75 – 100** |

- **Only the published number is flipped.** The sub-metrics, their limits from the source table, the tier weights (1, 2, 4, 8), "Excluded" and missing data are calculated exactly as for every KPI, in the same shared code. The flip is the last step, in `publish_kpi(..., higher_is_worse=True)`.
- **The order and the distances are kept.** A cluster whose weighted average is 10 points higher than another's has a Cluster Risk 10 points lower.
- **Set thresholds the other way round.** Any symptom, alert, or widget color range on `Cluster Risk Score` must treat high as bad: red from 75, not below 25. The pack's Extreme Capacity dashboard uses the score, with red from 75. The pack's other dashboards and reports use only the Risk sub-metrics.
- **"Worst" means highest.** That is why vSphere World uses the 90th percentile and the highest Cluster Risk, and the Periodic Cluster Check takes the high end of Cluster Risk and counts it red above 75.

## Worked examples

Two hosts, each with 32 cores (64 threads) and 512 GB of DRAM. Each runs four VMs of 4 vCPU and 16 GB. The monster size of these hosts is 16 vCPU (half of 32 cores) and 204.8 GB (40 % of 512 GB, less than 256 GB).

- **Low risk.** Both hosts at 40 % thread and 80 % core utilization (one running thread per running core), 50 % memory consumed, nothing ballooned, swapped or reserved.
  - Left out: the six rows in their excluded green, and Memory Tiering Latency (these hosts have no memory tiering).
  - Counted: CPU Imbalance 1 (100), Ballooned 0 (100), Zip Swap 0 (100), CPU Monster VM `4 / 16` = 0.25 (93.75), Memory Monster VM `16 / 204.8` = 0.08 (98).
  - Weighted average = `(100 + 100 + 100 + 93.75 + 98) / 5` = 98.35. Cluster Risk = `100 − 98.35` = **1.65**.
- **One busy host.** Host 1 at 90 % thread and 100 % core utilization. Host 2 at 30 % and 60 %.
  - CPU Thread Utilization 90 leaves its excluded green. It is at the start of red: 25 with weight 8.
  - CPU Imbalance of host 1 is `57.6 running threads / 32 running cores` = 1.8. Host 2 is 1.0. The worst, 1.8, is halfway through red: 12.5 with weight 8.
  - Weighted average = `(25 × 8 + 12.5 × 8 + 100 + 100 + 93.75 + 98) / (8 + 8 + 4)` = 34.59. Cluster Risk = `100 − 34.59` = **65.41**.

The same examples are checked by the tests in [`Management Pack/tests/test_cluster_risk_metrics.py`](../../../Management%20Pack/tests/test_cluster_risk_metrics.py).

## Known limitation: a worse sub-metric can lower Cluster Risk

> **Read this before using a change in Cluster Risk as a decision.**

A sub-metric that gets worse can make Cluster Risk go **down**. This happens when the sub-metric moves into a tier with a higher weight while it is still less bad than the sub-metrics already driving Cluster Risk.

### Why

Cluster Risk is 100 minus a weighted average, and the weight of a sub-metric depends on its tier. When a sub-metric moves into a tier with a higher weight, it counts more, and the weighted average moves toward that sub-metric's score. If that score is higher than the current weighted average, the average goes up, and Cluster Risk goes down.

The weight goes up in two cases:

| Case | Weight | Example |
| :--- | :--- | :--- |
| One of the six "Excluded" sub-metrics leaves green, so it is included for the first time | 0 → 2 | CPU Overcommit Ratio passes 1 after new VMs are deployed |
| Any sub-metric crosses into the next tier | doubles | Ballooned passes 1 % (green → yellow) |

The rule: Cluster Risk goes down when that sub-metric's own level, `100 − its score`, is below the current Cluster Risk. So it happens only when Cluster Risk is already high, driven by worse sub-metrics. When the other sub-metrics are green, a sub-metric that gets worse always raises Cluster Risk.

### Example with 5 sub-metrics

Sub-metric A is red. B moves just across its green limit into yellow. C, D and E stay green. All five are counted.

| Sub-metric | Before: score × weight | After: score × weight |
| :--- | :--- | :--- |
| A, red | 10 × 8 = 80 | 10 × 8 = 80 |
| **B, green → yellow** | **76 × 1 = 76** | **74 × 2 = 148** |
| C, D, E, green | 90 × 3 = 270 | 90 × 3 = 270 |
| Weighted average | 426 / 12 = 35.50 | 498 / 13 = 38.31 |
| **Cluster Risk** | **64.50** | **61.69** |

B got worse: its score fell from 76 to 74. In yellow its weight doubled, so its 74 now counts twice. That 74 is far above the average of 35.50, which A holds down. Counting it twice pulls the average up, and Cluster Risk falls by 2.81.

In this example B keeps lowering Cluster Risk until its score drops below 55.75, about three quarters of the way through yellow.

### Example: deploying VMs

The cluster of [One busy host](#worked-examples), at Cluster Risk 65.41. New idle VMs raise CPU Overcommit Ratio on the hosts. Every other sub-metric stays the same.

| CPU Overcommit Ratio | Tier | Score × weight | Cluster Risk |
| :--- | :--- | :--- | :--- |
| 0.5 | Excluded green | left out | 65.41 |
| 1.125 (ten 4 vCPU VMs, five per host) | yellow | 71.88 × 2 | **62.02** |
| 1.5 | yellow | 62.50 × 2 | **62.87** |
| 2.5 | orange | 37.50 × 4 | **64.93** |
| 2.8 | orange | 30.00 × 4 | 66.18 |
| 3.5 | red | 12.50 × 8 | 71.72 |

From 1.125 to 2.5, the overcommit ratio rises but Cluster Risk stays below 65.41. Only from about 2.6 is the sub-metric bad enough to raise Cluster Risk.

### What it affects

- **Close for Business.** The [Periodic Cluster Check](periodic-cluster-check.md) reads Cluster Risk in orange, from 50. A cluster just above 50 can drop into yellow after VMs are deployed, and open again.
- **Trends.** A falling Cluster Risk does not always mean less risk. Check the sub-metrics.
- **Every KPI.** All KPIs share this scoring. [Cluster Consumption](cluster-consumption.md) has the tier case only, because it has no Excluded sub-metrics. In the Performance KPIs, such as [Cluster Performance](cluster-performance.md), the effect is the other way round: a worse sub-metric can raise the score.

## Missing data

A sub-metric with no data is not published for that cycle, and it is left out of the KPI. It is never counted as 0, because a sub-metric value of 0 means "no risk".

A stat whose latest value is more than 10 minutes old counts as no data. A last known value is never used. See [No stale values](../../reference/metrics/README.md#no-stale-values).

- If the stats request to VCF Operations fails, only the property-based rows (the two Monster VM ratios) are scored.
- A host that VCF Operations does not know is left out.
- Overcommit and Monster VM count powered-on VMs only.

## Confirmed on a live system

Stats and their units: `cpu|utilization_average` (vCenter `cpu.utilization`), `cpu|coreUtilization_average` (vCenter `cpu.coreUtilization`), `cpu|reservedCapacity_average` (MHz), `mem|reservedCapacity_average` (KB), `mem|swapout_average`, `mem:DRAM|memory_tier_total_capacity` (KB), `mem|host_provisioned` (KB) and `mem:NVMe|latency.read_latest` (µs).

The properties endpoint `POST api/resources/properties/latest/query`, on VCF Operations 9.1.1. A text property comes back under `values`, a number under `data`; the code reads both. Tested with one host (cluster, cores, hyper-threading) and one VM (host, power state "Powered Off", vCPUs, memory). Both responses are kept in `tests/test_ops_inventory.py`.

The latest stats endpoint `POST api/resources/stats/latest/query`, on VCF Operations 9.1.1. Asked for a stat, it also returns every instance of it, such as `cpu:26|utilization_average` for CPU thread 26. The code keeps only the keys it asked for. The response is kept in `tests/test_ops_inventory.py`.

`net|packetsRx_summation_sum` and `net|packetsTx_summation_sum`, used by Bad Network Packets, are deactivated by default: see [Required Policy Settings](../../configuration-guide/policy.md).
