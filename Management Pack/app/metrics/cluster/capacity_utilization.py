#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Capacity Utilization: how much of the cluster's usable capacity is in use, CPU and memory.

What it is
----------
Two metrics per vSphere cluster, every collection cycle, under vCommunity|Capacity:

    CPU Utilization      sum of ESXi CPU Utilization (%) / (N - k)
    Memory Utilization   sum of ESXi Memory Consumed (%) / (N - k)

N is the number of hosts in the cluster, k the number of host failures vSphere HA tolerates (N+k). The k
spare hosts are capacity that must stay free for a host failure, so the usable capacity is N - k hosts.

It can be above 100 %. A 4-host N+1 cluster with every host at 90 % is 4 x 90 / 3 = 120 %: if a host
fails, the other three cannot hold the load. That is the point of the metric, so it is not capped.

Inputs, from VCF Operations, the same per-host values as Cluster Risk (cluster_risk_metrics.py):
    ESXi CPU Utilization   cpu|utilization_average: % of the host's CPU threads in use
    ESXi Memory Consumed   mem|consumed_average as a % of the host's DRAM

Memory uses Consumed only. Ballooned, compressed (zip) and swapped memory are not added: they are already
scored in Cluster Risk (Worst ESXi Memory Ballooned, Worst ESXi Memory Zip Swap).

Known limitations (see docs/capacity-utilization.md):
    - All hosts of the cluster are assumed to be the same size. A percentage of a big host and of a small
      host are added as if they were equal.
    - No value when a host of the cluster has no data: a missing host would make the cluster look emptier.
    - No failover level (HA off, percentage-based or dedicated-host admission control) counts as k = 0.

Used by the Daily Cluster Check (daily_cluster_check.py), which takes the 99th percentile of the 24 hours.
Called from: collectors/cluster/collectClusterData.py, once per cluster.
"""
from typing import Dict, List, Optional
from metrics.cluster.cluster_risk_metrics import CPU_THREAD_UTIL, memory_consumed_pct
from utils.ops_inventory import ClusterHa

GROUP = "Capacity"
CPU = "CPU Utilization"
MEMORY = "Memory Utilization"
METRICS = [CPU, MEMORY]


def cluster_utilization(host_values: List[Optional[float]], ha: ClusterHa) -> Optional[float]:
    """sum(host_values) / (N - k). None when a host has no data, or when N - k is 0 or less.

    host_values has one value per host found in the cluster, None meaning "no data". N is the larger of the
    cluster's host count and the hosts found, so a host that VCF Operations counts but did not return also
    means "no data". No failover level counts as k = 0.
    """
    n = max(int(ha.host_count or 0), len(host_values))
    k = int(ha.failover_level or 0)
    if n - k <= 0 or len(host_values) < n or None in host_values:
        return None
    return sum(host_values) / (n - k)


def utilization_values(host_ids: List[str], stats_by_host: Dict[str, Dict[str, float]],
                       ha: ClusterHa) -> Dict[str, Optional[float]]:
    """{CPU: %, MEMORY: %} of one cluster. None means "no data"."""
    host_stats = [stats_by_host.get(host_id, {}) for host_id in host_ids]
    return {
        CPU: cluster_utilization([stats.get(CPU_THREAD_UTIL) for stats in host_stats], ha),
        MEMORY: cluster_utilization([memory_consumed_pct(stats) for stats in host_stats], ha),
    }


def publish(cluster_obj, values: Dict[str, Optional[float]]) -> None:
    """Publishes the values that have data, rounded to two decimals."""
    for name, value in values.items():
        if value is not None:
            cluster_obj.with_metric(f"vCommunity|{GROUP}|{name}", round(value, 2))
