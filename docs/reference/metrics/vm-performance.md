# VM Performance KPI

**VM Performance** is a 0 to 100 % score for a virtual machine. 100 is best. It scores the VM as a virtual motherboard: whether ESXi gives it the CPU, memory, disk and network it asks for. It combines 9 sub-metrics, and the worse a sub-metric is, the more weight it gets.

What happens inside Windows or Linux is scored separately, by [Guest OS Performance](guest-os-performance.md).

It is published on every powered-on VM as `vCommunity|VM Performance|VM Performance Score`. A powered-off VM gets no score.

Code: [`Management Pack/app/metrics/vm/vm_performance_metrics.py`](../../../Management%20Pack/app/metrics/vm/vm_performance_metrics.py)

Source of the sub-metrics and limits: [`formula/vm-performance.png`](formula/vm-performance.png)

## VM Guest OS KPI

`vCommunity|VM Guest OS KPI` gives one score per VM: the average of VM Performance and [Guest OS Performance](guest-os-performance.md).

- A VM without Guest OS Performance, such as a VM without VMware Tools, gets its VM Performance score.
- A VM without a VM Performance score gets no VM Guest OS KPI, even when it has Guest OS Performance.

It replaces the "vSphere VM Performance" super metric, and it feeds [Business Application Performance](business-application-performance.md). Code: [`vm_guest_os_kpi.py`](../../../Management%20Pack/app/metrics/vm/vm_guest_os_kpi.py).

## Step 1: Collect the 9 sub-metrics

Eight sub-metrics are stats the VM already has. The pack reads them and does not publish them again. Memory Zip Swap is calculated and published.

| Group | Sub-metric | Source |
| :--- | :--- | :--- |
| VM contention | CPU Co-Stop | `cpu\|20_sec_peak_costopPct` |
| VM contention | CPU Ready | `cpu\|20_sec_peak_readyPct` |
| VM contention | CPU Overlap | `cpu\|20_sec_peak_overlap` (%) |
| VM contention | Memory Contention | `mem\|20_sec_peak_host_contentionPct` |
| VM contention | Disk Latency | `virtualDisk\|20_sec_peak_totalLatency_average` |
| VM contention | Network Dropped Tx | `net\|droppedTxPct_max` |
| VM utilization | CPU Run | `cpu\|net_run` |
| IaaS high utilization | Memory Ballooned | `mem\|balloonPct` |
| IaaS high utilization | Memory Zip Swap | Calculated: `(mem\|compressed_average + mem\|swapped_average) / guest\|used_memory × 100`. Published as `vCommunity\|VM Performance\|Memory Zip Swap`. |

The 20-second peaks are used where they exist, rather than the 5-minute averages, so short contention shows.

Memory Zip Swap is divided by the memory the guest OS uses, not by the VM's configured memory. Configured memory includes memory the guest does not use, so dividing by it would make the percentage smaller and under-report the problem. This is the formula of the "vSphere VM Memory Zip Swap" super metric, which this metric replaces.

## Step 2 and 3: Score each sub-metric, then combine

The scoring is the same for every KPI. See [How the pack scores a KPI](../../concepts/kpi-scoring-models.md#how-the-pack-scores-a-kpi).

## Thresholds

Every sub-metric is lower-is-better, and 0 is best.

| Sub-metric | Unit | Green ends at | Yellow ends at | Orange ends at | Score hits 0 at |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CPU Co-Stop | % | 1 | 2 | 4 | 8 |
| CPU Ready | % | 2 | 4 | 8 | 16 |
| CPU Overlap | % | Excluded (below 0.5) | 1 | 2 | 4 |
| Memory Contention | % | 0.5 | 1 | 2 | 4 |
| Disk Latency | ms | 10 | 20 | 40 | 80 |
| Network Dropped Tx | % | Excluded (exactly 0) | 0.5 | 1 | 2 |
| CPU Run | % | Excluded (below 95) | 97 | 99 | 100 |
| Memory Ballooned | % | 2 | 4 | 8 | 16 |
| Memory Zip Swap | % | 0.25 | 0.5 | 1 | 2 |

**Excluded.** The source table marks three green ranges "Excluded". While a value is in that range, it is left out of the KPI, as [described for every KPI](../../concepts/kpi-scoring-models.md#skip-when-green).

- CPU Overlap below 0.5 %: some overlap is normal and says nothing about performance.
- Network Dropped Tx at exactly 0: dropped packets are rare. Any dropped packet is yellow.
- CPU Run below 95 %: a VM that is not busy tells you nothing about its performance. Above 95 %, the VM is too small for its load.

## Worked examples

- **Nothing wrong.** CPU Overlap, Network Dropped Tx and CPU Run are in their excluded green and left out. The other 6 score 100 with weight 1. KPI = **100**.
- **The same, except CPU Ready = 10** (red tier):
  - 10 is a quarter of the way through red (8 to 16), so it scores `25 − (¼ × 25) = 18.75`, with weight `2^(81.25 / 25)` ≈ 9.51.
  - KPI = `(5 × 100 + 18.75 × 9.51) / (5 + 9.51)` ≈ **46.74**.
- **The same as the first, except CPU Run = 98 %** (orange tier):
  - 98 is halfway through orange (97 to 99), so it scores 37.5, with weight 5.66.
  - KPI = `(6 × 100 + 37.5 × 5.66) / (6 + 5.66)` ≈ **69.67**.
- **The same as the first, except 0.25 % dropped packets** (yellow tier):
  - 0.25 is halfway through yellow (0 to 0.5), so it scores 62.5, with weight 2.83.
  - KPI = `(6 × 100 + 62.5 × 2.83) / (6 + 2.83)` ≈ **87.99**.

The tests in [`Management Pack/tests/test_vm_performance_metrics.py`](../../../Management%20Pack/tests/test_vm_performance_metrics.py) check the same examples.

## Missing data

A sub-metric with no data is left out of the KPI. It is never counted as best.

A stat whose latest value is more than 10 minutes old counts as no data. See [No stale values](README.md#no-stale-values).

- A VM without VMware Tools has no Memory Zip Swap, because that needs `guest|used_memory`. Its KPI is built from the other sub-metrics.
- If no sub-metric has data, the KPI is not published.
- A powered-off VM gets no KPI, because its stats are old. The power state is the VCF Operations property `summary|runtime|powerState`, and a VM counts when it is "Powered On".

## Changing the KPI

The code follows the source table: one section per row, in the same order, with the row's limits and the source of its value, either a VM stat or a formula.

- To change a limit, edit the row's section.
- To add a sub-metric, add a section with its limits and its VM stat or formula, and add it to `ROWS`.
- To exclude a green range, set the last value of the row to `True`. For a green that is exactly 0, also set the green limit to 0.

The adapter definition reads the same table, so nothing else needs to change.
