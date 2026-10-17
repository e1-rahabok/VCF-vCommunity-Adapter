# Capacity Utilization

**Capacity Utilization** shows how much of a vSphere cluster's usable capacity is in use, for CPU and for memory. Usable capacity leaves out the hosts that vSphere HA keeps free for a host failure.

It feeds the [Periodic Cluster Check](periodic-cluster-check.md), which takes its 99th percentile over each window (24 hours by default).

Code: [`Management Pack/app/metrics/cluster/capacity_utilization.py`](../../../Management%20Pack/app/metrics/cluster/capacity_utilization.py)

## Known limitations

> **Read this before using the metrics.**

- **All ESXi hosts of the cluster are assumed to be the same size.** The host percentages are added up as if every host had the same CPU and memory. In a cluster that mixes big and small hosts, a busy small host counts as much as a busy big host, so the value can be off in either direction.
- **It can be above 100 %.** This is intended, not an error. Above 100 %, the hosts left after a host failure cannot hold the load. See the [example](#example).
- **Memory is Consumed only.** Ballooned, compressed (zip) and swapped memory are not added, because they are already scored in [Cluster Risk](cluster-risk.md) (Worst ESXi Memory Ballooned, Worst ESXi Memory Zip Swap).
- **A disconnected host counts as gone, even if its VMs still run.** When a host is disconnected, neither vCenter nor VCF Operations can see whether its VMs run, or how busy it is. Its load is then missing, so the value is understated while the host stays disconnected.
- **No last known values.** A host whose latest CPU or memory value is more than 10 minutes old counts as gone. See [No stale values](../../reference/metrics/README.md#no-stale-values).
- **No HA failover level counts as N+0.** That is the case when HA is off, or when admission control uses a percentage or dedicated failover hosts. The value is then divided by all hosts, so it is lower than with a host set aside.
- **No value when no capacity is left**: N − max(k, gone hosts) is 0 or less, for example when every host is gone, or a 1-host cluster set to N+1.

## The metrics

Published on every vSphere cluster, every collection cycle, under `vCommunity|Capacity`, in %.

| Metric | Calculation |
| :--- | :--- |
| `vCommunity\|Capacity\|CPU Utilization` | Sum of the ESXi CPU Utilization (%) of the running hosts ÷ (N − max(k, gone hosts)) |
| `vCommunity\|Capacity\|Memory Utilization` | Sum of the ESXi Memory Consumed (%) of the running hosts ÷ (N − max(k, gone hosts)) |

- **N** is the number of hosts in the cluster: `summary|total_number_hosts`, or the hosts found when that is more.
- **k** is the number of host failures vSphere HA tolerates (N+k): `configuration|dasConfig|hostFailoverLevel`, the same property as the former "Clusters Availability" super metric and [Operational Availability](operational-availability.md).

### Gone hosts

A host is **gone** when it cannot run VMs, or when nothing current is known about it:

| Host state | Why it is gone |
| :--- | :--- |
| Not responding | Dead, or cut off from vCenter. vSphere HA restarts its VMs elsewhere. |
| Disconnected | Nothing current is known about it or its VMs. |
| Powered off, or in standby (DPM) | Runs no VM. |
| In maintenance mode | vSphere allows no running VM on a host in maintenance mode. A host still *entering* maintenance mode counts as running, because its VMs are still on it. |
| No current value | No CPU or memory value in the last 10 minutes, or counted by VCF Operations but not found. |

- A gone host adds **0** to the sum.
- It **uses up an HA spare first**: up to k gone hosts is what N+k is for, so the divisor stays N − k.
- **Beyond k**, each gone host takes its capacity away, and the value goes up. Overstating is preferred to understating.

### Scenarios

A 4-host cluster, N+1. On paper the maximum is 4 × 100 ÷ 3 = 133 %.

| Host 1 | Hosts 2 – 4 | Calculation | Utilization |
| :--- | :--- | :--- | :--- |
| Running, 100 % | 100 % | 400 ÷ (4 − max(1, 0)) | **133 %** |
| Gone (any state above) | 100 % | 300 ÷ (4 − max(1, 1)) | **100 %** |
| Entering maintenance mode, 100 % | 100 % | 400 ÷ 3 | **133 %** |
| Hosts 1 and 2 gone | hosts 3 – 4 at 100 % | 200 ÷ (4 − max(1, 2)) | **100 %** |
| Hosts 1 and 2 gone | hosts 3 – 4 at 80 % | 160 ÷ 2 | **80 %** |
| All 4 gone | | 0 ÷ 0 | blank |

**Inputs**, from VCF Operations, the same per-host values as [Cluster Risk](cluster-risk.md), plus the host state:

- ESXi CPU Utilization: `cpu|utilization_average`, the share of the host's CPU threads in use.
- ESXi Memory Consumed: `mem|consumed_average` as a share of the host's DRAM (`mem:DRAM|memory_tier_total_capacity`, or `mem|host_provisioned` when that has no value). A memory tier such as NVMe is not added.
- Host state, as properties: `runtime|connectionState`, `runtime|powerState`, `runtime|maintenanceState`.

## Design considerations

- **Divided by N − max(k, gone hosts), not N.** The k spare hosts must stay free for a host failure, so they are not usable capacity. A failed host, or one in maintenance mode, uses up a spare: that is what N+k is for.
- **Availability is a separate metric.** A gone host lowers [Operational Availability](operational-availability.md). Capacity Utilization keeps showing a value as long as a host runs.
- **Not capped at 100 %.** A value above 100 % is the warning: after a host failure the cluster is overcommitted.
- **No extra requests.** The host stats are the ones Cluster Risk already reads. The host count and failover level are read once per cycle for all clusters.
- All inputs come from VCF Operations. Nothing is read from vCenter.

## Example

A 4-host cluster, N+1. Each host is at 90 % CPU Utilization.

- CPU Utilization = `(90 + 90 + 90 + 90) ÷ (4 − 1)` = **120 %**.
- If one host fails, the three left must run 360 % of one host's load: 120 % each. They cannot.

The same examples are checked by the tests in [`Management Pack/tests/test_capacity_utilization.py`](../../../Management%20Pack/tests/test_capacity_utilization.py).
