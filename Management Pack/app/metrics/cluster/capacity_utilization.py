#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Capacity Utilization: how much of the cluster's usable capacity is in use, CPU and memory.

What it is
----------
Two metrics per vSphere cluster, every collection cycle, under vCommunity|Capacity:

    CPU Utilization      sum of ESXi CPU Utilization (%) of the running hosts / (N - max(k, gone))
    Memory Utilization   sum of ESXi Memory Consumed (%) of the running hosts / (N - max(k, gone))

N is the number of hosts in the cluster, k the number of host failures vSphere HA tolerates (N+k).
The k spare hosts are capacity that must stay free for a host failure, so the usable capacity is N - k hosts.

A host is gone when it cannot run VMs, or when nothing current is known about it:
    - not connected (disconnected, or not responding: dead or cut off),
    - powered off or in standby,
    - fully in maintenance mode (vSphere allows no running VM on it; entering maintenance mode still counts),
    - no current value for the metric (none, or older than STALE_AFTER_MINUTES in utils/ops_stats.py).
A gone host adds nothing, and uses up an HA spare first: up to k gone hosts is what N+k is for, so the
denominator stays N - k. Beyond k, each gone host takes its capacity away, and the value goes up. Overstating
is preferred to understating. Last known values are never used.

It can be above 100 %. A 4-host N+1 cluster with every host at 90 % is 4 x 90 / 3 = 120 %: if a host
fails, the other three cannot hold the load. That is the point of the metric, so it is not capped.

Inputs, from VCF Operations, the same per-host values as Cluster Risk (cluster_risk_metrics.py):
    ESXi CPU Utilization   cpu|utilization_average: % of the host's CPU threads in use
    ESXi Memory Consumed   mem|consumed_average as a % of the host's DRAM
    Host state             properties runtime|connectionState, runtime|powerState, runtime|maintenanceState

Memory uses Consumed only. Ballooned, compressed (zip) and swapped memory are not added: they are already
scored in Cluster Risk (Worst ESXi Memory Ballooned, Worst ESXi Memory Zip Swap).

Known limitations (see docs/capacity-utilization.md):
    - All hosts of the cluster are assumed to be the same size. A percentage of a big host and of a small
      host are added as if they were equal.
    - A disconnected host whose VMs still run counts as gone: its load is not visible, so it is understated.
    - No failover level (HA off, percentage-based or dedicated-host admission control) counts as k = 0.

Used by the Daily Cluster Check (daily_cluster_check.py), which takes the 99th percentile of the 24 hours.
Called from: collectors/cluster/collectClusterData.py, once per cluster.
"""
from typing import Dict, List, Optional
from metrics.cluster.cluster_risk_metrics import CPU_THREAD_UTIL, memory_consumed_pct
from utils.ops_inventory import ClusterHa, HostInfo

GROUP = "Capacity"
CPU = "CPU Utilization"
MEMORY = "Memory Utilization"
METRICS = [CPU, MEMORY]


# Host states that mean the host runs no VM. Compared without case and spaces: VCF Operations may store
# "Powered Off" or "poweredOff".
NOT_RUNNING_POWER_STATES = {"poweredoff", "standby"}
IN_MAINTENANCE = "inmaintenance"
CONNECTED = "connected"


def _state(value: Optional[str]) -> Optional[str]:
    return value.replace(" ", "").lower() if value else None


def host_is_gone(host: HostInfo, value: Optional[float]) -> bool:
    """True when the host cannot run VMs, or when value, its current metric value, is None."""
    if value is None:
        return True
    connection = _state(host.connection_state)
    if connection is not None and connection != CONNECTED:
        return True
    if _state(host.power_state) in NOT_RUNNING_POWER_STATES:
        return True
    return _state(host.maintenance_state) == IN_MAINTENANCE


def cluster_utilization(hosts: List[HostInfo], values: List[Optional[float]], ha: ClusterHa) -> Optional[float]:
    """sum of the running hosts' values / (N - max(k, gone)). None when no capacity is left.

    hosts and values go together: values[i] is the current value of hosts[i], None meaning "no data".
    N is the larger of the cluster's host count and the hosts found: a host that VCF Operations counts but
    did not return is gone. No failover level counts as k = 0.
    """
    n = max(int(ha.host_count or 0), len(hosts))
    k = int(ha.failover_level or 0)
    running = [value for host, value in zip(hosts, values) if not host_is_gone(host, value)]
    gone = n - len(running)
    usable = n - max(k, gone)
    if usable <= 0:
        return None
    return sum(running) / usable


def utilization_values(hosts: List[HostInfo], stats_by_host: Dict[str, Dict[str, float]],
                       ha: ClusterHa) -> Dict[str, Optional[float]]:
    """{CPU: %, MEMORY: %} of one cluster. None means "no data"."""
    host_stats = [stats_by_host.get(host.id, {}) for host in hosts]
    return {
        CPU: cluster_utilization(hosts, [stats.get(CPU_THREAD_UTIL) for stats in host_stats], ha),
        MEMORY: cluster_utilization(hosts, [memory_consumed_pct(stats) for stats in host_stats], ha),
    }


def publish(cluster_obj, values: Dict[str, Optional[float]]) -> None:
    """Publishes the values that have data, rounded to two decimals."""
    for name, value in values.items():
        if value is not None:
            cluster_obj.with_metric(f"vCommunity|{GROUP}|{name}", round(value, 2))
