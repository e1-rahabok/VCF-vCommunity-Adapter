# Capacity Utilization

**Capacity Utilization** shows how much of a vSphere cluster's usable capacity is in use, for CPU and for memory. Usable capacity leaves out the hosts that vSphere HA keeps free for a host failure.

It feeds the [Daily Cluster Check](daily-cluster-check.md), which takes its 99th percentile over 24 hours.

Code: [`Management Pack/app/metrics/cluster/capacity_utilization.py`](../Management%20Pack/app/metrics/cluster/capacity_utilization.py)

## Known limitations

> **Read this before using the metrics.**

- **All ESXi hosts of the cluster are assumed to be the same size.** The host percentages are added up as if every host had the same CPU and memory. In a cluster that mixes big and small hosts, a busy small host counts as much as a busy big host, so the value can be off in either direction.
- **It can be above 100 %.** This is intended, not an error. Above 100 %, the hosts left after a host failure cannot hold the load. See the [example](#example).
- **Memory is Consumed only.** Ballooned, compressed (zip) and swapped memory are not added, because they are already scored in [Cluster Risk](cluster-risk-kpi.md) (Worst ESXi Memory Ballooned, Worst ESXi Memory Zip Swap).
- **No value when a host of the cluster has no data**, including a host that VCF Operations counts in the cluster but did not return. Leaving it out would make the cluster look emptier than it is.
- **No HA failover level counts as N+0.** That is the case when HA is off, or when admission control uses a percentage or dedicated failover hosts. The value is then divided by all hosts, so it is lower than with a host set aside.
- **No value when N − k is 0 or less**, for example a 1-host cluster set to N+1.

## The metrics

Published on every vSphere cluster, every collection cycle, under `vCommunity|Capacity`, in %.

| Metric | Calculation |
| :--- | :--- |
| `vCommunity\|Capacity\|CPU Utilization` | Sum of the ESXi CPU Utilization (%) of the hosts ÷ (N − k) |
| `vCommunity\|Capacity\|Memory Utilization` | Sum of the ESXi Memory Consumed (%) of the hosts ÷ (N − k) |

- **N** is the number of hosts in the cluster: `summary|total_number_hosts`.
- **k** is the number of host failures vSphere HA tolerates (N+k): `configuration|dasConfig|hostFailoverLevel`, the same property as the former "Clusters Availability" super metric and [Operational Availability](operational-availability.md).

**Inputs**, from VCF Operations, the same per-host values as [Cluster Risk](cluster-risk-kpi.md):

- ESXi CPU Utilization: `cpu|utilization_average`, the share of the host's CPU threads in use.
- ESXi Memory Consumed: `mem|consumed_average` as a share of the host's DRAM (`mem:DRAM|memory_tier_total_capacity`, or `mem|host_provisioned` when that has no value). A memory tier such as NVMe is not added.

## Design considerations

- **Divided by N − k, not N.** The k spare hosts must stay free for a host failure, so they are not usable capacity.
- **Not capped at 100 %.** A value above 100 % is the warning: after a host failure the cluster is overcommitted.
- **No extra requests.** The host stats are the ones Cluster Risk already reads. The host count and failover level are read once per cycle for all clusters.
- All inputs come from VCF Operations. Nothing is read from vCenter.

## Example

A 4-host cluster, N+1. Each host is at 90 % CPU Utilization.

- CPU Utilization = `(90 + 90 + 90 + 90) ÷ (4 − 1)` = **120 %**.
- If one host fails, the three left must run 360 % of one host's load: 120 % each. They cannot.

The same examples are checked by the tests in [`Management Pack/tests/test_capacity_utilization.py`](../Management%20Pack/tests/test_capacity_utilization.py).
