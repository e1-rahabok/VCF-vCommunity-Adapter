# ESXi Performance KPI

**ESXi Performance** is a 0 to 100 % score for an ESXi host. 100 is best. It measures the contention the VMs on the host have now. It shows how bad the contention is, not why it happens.

It looks at the powered-on VMs on the host in two ways:

- The worst VM shows a problem that hits one VM hard.
- The 90th percentile across the VMs shows a problem that many VMs have: 90 % of the VMs are at or below this value.

The KPI and its 9 sub-metrics are published on the host object under `vCommunity|ESXi Performance`. The KPI is `vCommunity|ESXi Performance|ESXi Performance Score`.

Code: [`Management Pack/app/metrics/host/esxi_performance_metrics.py`](../../../Management%20Pack/app/metrics/host/esxi_performance_metrics.py)

Source of the limits: [`formula/esxi-performance.png`](formula/esxi-performance.png)

## The 9 sub-metrics

Every sub-metric is lower-is-better, and 0 is best. The VM stats are 20-second peaks.

| Group | Sub-metric | Unit | Green ends at | Yellow ends at | Orange ends at | Score hits 0 at |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Worst VM | Worst VM CPU Ready | % | 4 | 8 | 16 | 32 |
| Worst VM | Worst VM CPU Co-Stop | % | 2 | 4 | 8 | 16 |
| Worst VM | Worst VM Memory Latency | % | 1 | 2 | 4 | 8 |
| Worst VM | Worst VM Disk Latency (read and write, any virtual disk) | ms | 40 | 80 | 160 | 320 |
| 90th percentile | 90th Percentile VM CPU Ready | % | 1 | 2 | 4 | 8 |
| 90th percentile | 90th Percentile VM CPU Co-Stop | % | 0.5 | 1 | 2 | 4 |
| 90th percentile | 90th Percentile VM Memory Latency | % | 0.5 | 1 | 2 | 4 |
| 90th percentile | 90th Percentile VM Disk Latency (read and write) | ms | 20 | 40 | 60 | 80 |
| ESXi | ESXi Bad Network Packets (errored + dropped) | % | Excluded (exactly 0) | 0.2 | 0.4 | 0.8 |

Bad network packets are green only at exactly 0, and the source table marks that range "Excluded". Any bad packet is yellow. While the value is 0 the sub-metric is left out of the KPI, because bad packets are rare and a constant 100 would dilute the other sub-metrics.

## How the score is calculated

Like every KPI, see [How the pack scores a KPI](../../concepts/kpi-scoring-models.md#how-the-pack-scores-a-kpi): each sub-metric is scored from its limits, and the KPI is the weighted average of the scores. Scoring examples are in [Cluster Performance KPI](cluster-performance.md#worked-examples). The code is [`kpi_score.py`](../../../Management%20Pack/app/metrics/kpi_score.py).

## How each sub-metric is calculated

These are the sub-metrics of [Cluster Performance](cluster-performance.md#step-1-collect-the-9-sub-metrics), measured over the VMs of one host instead of a whole cluster. The formulas are defined once, in [`metrics/vm/contention_by_vms.py`](../../../Management%20Pack/app/metrics/vm/contention_by_vms.py).

- The 8 VM sub-metrics are the worst value and the 90th percentile of `cpu|20_sec_peak_readyPct`, `cpu|20_sec_peak_costopPct`, `mem|20_sec_peak_host_contentionPct` and `virtualDisk|20_sec_peak_totalLatency_average`, over the powered-on VMs on the host. A VM runs on the host named in its `summary|parentHost` property, and it is powered on when `summary|runtime|powerState` is "Powered On". Both properties are read from VCF Operations.
- Bad network packets are `(errorsRx + errorsTx + droppedRx + droppedTx) / (packetsRx + packetsTx) × 100` for the host, in the last collection cycle (5 minutes), as the "ESXi Bad Network Packets" super metric did. The value is never averaged over a longer time, because that would hide a spike. Two of the counters, Total Packets Received and Transmitted, are deactivated by default in VCF Operations. Activate them first: see [Policy](../../configuration-guide/policy.md).

The stats of all VMs and all hosts of the vCenter are read in bulk, once per collection cycle.

## Worked examples

- **Nothing wrong.** Bad packets are 0 and left out. The other 8 score 100. KPI = **100**.
- **One VM of ten with 200 ms disk latency.** Worst VM Disk Latency is a quarter of the way through red (160 to 320): 18.75 with weight 9.51. The 90th percentile is the 9th lowest of the 10 VMs, so it stays 0. KPI = `(7 × 100 + 18.75 × 9.51) / (7 + 9.51)` ≈ **53.19**. With fewer than 10 VMs, the 90th percentile is the worst VM, so 90th Percentile VM Disk Latency would also be 200 and the KPI about 24.7.
- **A host with no powered-on VMs.** No VM sub-metric has data, and bad packets are 0 and left out. Nothing is wrong, so the KPI is **100**.

The tests in [`Management Pack/tests/test_esxi_performance_metrics.py`](../../../Management%20Pack/tests/test_esxi_performance_metrics.py) check the same examples.

## Missing data

A sub-metric with no data is not published for that cycle, and it is left out of the KPI. It is never counted as 0. A host that vCenter does not report as connected gets no KPI.

A stat whose latest value is more than 10 minutes old counts as no data. See [No stale values](README.md#no-stale-values).
