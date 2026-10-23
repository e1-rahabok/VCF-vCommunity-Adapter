#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Consumption KPI.

What it is
----------
One 0-100 % score per vSphere cluster: how much of the cluster's Usable Capacity is consumed. 0 is nothing
consumed, 100 is fully consumed: higher is worse, like Cluster Risk. Unlike Cluster Risk, it is cluster-wide, not
the worst ESXi host: the hosts are added up, so a big host counts more than a small one. Saturation (ballooned,
swapped and zipped memory) is not contention, because nothing is slow yet. It is real consumption, so it has its
own rows.

How this file is laid out
-------------------------
It follows the model, not the code:

  Part 1  Usable Capacity. One per resource, calculated once per cluster, and used by every row of that resource:
            CPU Usable Capacity      in threads       row 1
            Memory Usable Capacity   in DRAM          rows 2, 4, 5
                                     in NVMe tier     row 3
  Part 2  The 5 rows, one section each, in the order of the source table. Each section has the row's limits,
          what it adds up over the hosts, and the Usable Capacity it divides by. To add, change or remove a row,
          change only its section and its line in METRICS.
  Part 3  The KPI: score the rows and publish them.

Published on the cluster as:
    vCommunity|Cluster Consumption|Cluster Consumption Score    the KPI
    vCommunity|Cluster Consumption|<row name>                   each of the 5 rows

Called from: collectors/cluster/collectClusterData.py, once per cluster.
Used by the Periodic Cluster Check (periodic_cluster_check.py).
Description for people who do not read code: docs/reference/metrics/cluster-consumption.md
Where the limits come from: docs/reference/metrics/formula/cluster-consumption.png. No green range is "Excluded".
"""
import logging
from typing import Dict, List, NamedTuple, Optional
from aria.ops.object import Object
from metrics.kpi_score import Metric, percent, publish_kpi
from metrics.cluster.capacity_utilization import host_is_gone
from metrics.cluster.cluster_risk_metrics import (
    CPU_THREAD_UTIL, MEM_CONSUMED, MEM_BALLOONED, MEM_COMPRESSED, MEM_SWAPPED, dram_capacity_kb,
)
from utils.ops_inventory import HostInfo

logger = logging.getLogger(__name__)

GROUP = "Cluster Consumption"
KPI_NAME = "Cluster Consumption"
# The key of the KPI metric. It must differ from GROUP, see cluster_risk_metrics.KPI_KEY.
KPI_KEY = "Cluster Consumption Score"
# Published as 100 minus the score: 100 = fully consumed. See publish_kpi() in metrics/kpi_score.py.
HIGHER_IS_WORSE = True
# The KPI of a cluster with no Usable Capacity: fully consumed.
FULL = 100.0

StatsByHost = Dict[str, Dict[str, float]]


# =================================================================================================================
# Part 1. Usable Capacity
# =================================================================================================================
#
# Usable Capacity = Total Capacity - HA - Buffer. It is what the VMs of the cluster may use: the capacity kept for
# a host failure (HA admission control) and the Capacity Buffer (Demand) of the policy are not for VMs.
#
# VCF Operations calculates it per cluster, in MHz for CPU and in KB for memory. The pack counts CPU Usable Capacity
# in THREADS, not MHz, which differs from VCF Operations on purpose: capacity is about quantity, not quality. It is
# how many VMs fit (space), not how fast they run (speed), and MHz measures speed.
#
# How the threads are obtained: VCF Operations' Usable Capacity is taken as a percentage of its Total Capacity, and
# that percentage is applied to the threads of the running hosts. No step converts MHz to threads, so this is exact
# only when every host has the same clock speed and the same hyper-threading setting. Memory is done the same way,
# and the memory percentage is applied to the NVMe tier too. Both are known limitations, in the doc.
#
# The hosts that count are the running hosts with data (capacity_utilization.host_is_gone): a host in maintenance
# mode, disconnected, powered off or in standby adds no capacity, because no VM can use it.

# Cluster stats of VCF Operations, read once per cycle for all clusters by the cluster collector.
CPU_USABLE = "cpu|demand|usableCapacity"            # MHz, Total - HA - Buffer
CPU_TOTAL = "cpu|capacity_provisioned"              # MHz
MEM_USABLE = "mem|demand|usableCapacity"            # KB, Total - HA - Buffer
MEM_TOTAL = "mem|host_provisioned"                  # KB
CLUSTER_STATS = [CPU_USABLE, CPU_TOTAL, MEM_USABLE, MEM_TOTAL]

# Host stats of the NVMe memory tier, read once per cycle for all hosts. Only hosts with memory tiering have them.
# The CPU and DRAM host stats are the ones Cluster Risk already read this cycle (cluster_risk_metrics.HOST_STATS).
NVME_TIER_USAGE = "mem:NVMe|tier.usage"             # MB in use
NVME_TIER_SIZE = "mem:NVMe|memory_tier_size"        # KB
HOST_STATS = [NVME_TIER_USAGE, NVME_TIER_SIZE]


class UsableCapacity(NamedTuple):
    """The Usable Capacity of one cluster, per resource, and the hosts each one counts.

    A capacity is None when VCF Operations did not report it (no data), and 0 when HA and the Buffer leave nothing
    to VMs (the cluster is full).
    """
    cpu_threads: Optional[float]
    cpu_hosts: List[HostInfo]
    dram_kb: Optional[float]
    dram_hosts: List[HostInfo]
    nvme_tier_kb: Optional[float]
    nvme_tier_hosts: List[HostInfo]


def usable_percent(cluster_stats: Dict[str, float], usable_key: str, total_key: str) -> Optional[float]:
    """Usable Capacity as a % of Total Capacity, as VCF Operations reports them. None when either is missing.

    0 is a real answer: the cluster has capacity, but HA and the Buffer leave none of it to VMs, for example when HA
    tolerates one host failure and only one host runs. Such a cluster is full.
    """
    usable = cluster_stats.get(usable_key)
    total = cluster_stats.get(total_key)
    if usable is None or not total or total <= 0:
        return None
    return max(usable, 0.0) / total * 100.0


def has_no_usable_capacity(cluster_stats: Dict[str, float]) -> bool:
    """True when the cluster has CPU or memory, but none of it is usable by VMs: it is full."""
    return (usable_percent(cluster_stats, CPU_USABLE, CPU_TOTAL) == 0.0
            or usable_percent(cluster_stats, MEM_USABLE, MEM_TOTAL) == 0.0)


def host_is_running(host: HostInfo, stats_by_host: StatsByHost) -> bool:
    """True when the host can run VMs and reports its CPU: not down, powered off, in maintenance mode or
    disconnected. A cluster with no running host has no consumption at all."""
    return not host_is_gone(host, stats_by_host.get(host.id, {}).get(CPU_THREAD_UTIL))


def usable_capacity(hosts: List[HostInfo], stats_by_host: StatsByHost, tier_stats_by_host: StatsByHost,
                    cluster_stats: Dict[str, float]) -> UsableCapacity:
    """The Usable Capacity of the cluster, per resource, in the unit its rows need."""
    cpu_percent = usable_percent(cluster_stats, CPU_USABLE, CPU_TOTAL)
    memory_percent = usable_percent(cluster_stats, MEM_USABLE, MEM_TOTAL)

    # CPU: the running hosts that report their CPU utilization, counted in threads.
    cpu_hosts = [host for host in hosts if host.threads and host_is_running(host, stats_by_host)]
    cpu_threads = sum(host.threads for host in cpu_hosts)

    # DRAM: the running hosts that report their DRAM and their consumed memory. Never DRAM plus a memory tier.
    dram_hosts = [host for host in hosts
                  if dram_capacity_kb(stats_by_host.get(host.id, {})) is not None
                  and not host_is_gone(host, stats_by_host.get(host.id, {}).get(MEM_CONSUMED))]
    dram_kb = sum(dram_capacity_kb(stats_by_host[host.id]) for host in dram_hosts)

    # NVMe tier: the running hosts that have a tier and report its usage. Never the DRAM.
    nvme_tier_hosts = [host for host in hosts
                       if tier_stats_by_host.get(host.id, {}).get(NVME_TIER_SIZE)
                       and not host_is_gone(host, tier_stats_by_host.get(host.id, {}).get(NVME_TIER_USAGE))]
    nvme_tier_kb = sum(tier_stats_by_host[host.id][NVME_TIER_SIZE] for host in nvme_tier_hosts)

    return UsableCapacity(
        cpu_threads=_apply(cpu_percent, cpu_threads, cpu_hosts), cpu_hosts=cpu_hosts,
        dram_kb=_apply(memory_percent, dram_kb, dram_hosts), dram_hosts=dram_hosts,
        nvme_tier_kb=_apply(memory_percent, nvme_tier_kb, nvme_tier_hosts), nvme_tier_hosts=nvme_tier_hosts,
    )


def _apply(usable_pct: Optional[float], capacity: float, counted_hosts: List[HostInfo]) -> Optional[float]:
    """The Usable Capacity in the hosts' own unit. None when VCF Operations reported none, or no host counts."""
    if usable_pct is None or not counted_hosts:
        return None
    return capacity * usable_pct / 100.0


def _add_up(hosts: List[HostInfo], stats_by_host: StatsByHost, stat_keys: List[str]) -> Optional[float]:
    """The stats in stat_keys, added up over the hosts. None when any host lacks one: never a partial sum."""
    total = 0.0
    for host in hosts:
        values = [stats_by_host.get(host.id, {}).get(key) for key in stat_keys]
        if None in values:
            return None
        total += sum(values)
    return total


def _consumed(used: Optional[float], usable: Optional[float]) -> Optional[float]:
    """used as a % of Usable Capacity. None when either is missing, or there is no Usable Capacity."""
    if used is None or not usable:
        return None
    return percent(used, usable)


# =================================================================================================================
# Part 2. The 5 rows
# =================================================================================================================
#
# Every row is "lower is better", in % of the Usable Capacity of its resource. The five numbers of each Metric are
# the values where its score is 100, 75, 50, 25 and 0.
#       name   unit   best  green  yellow  orange  zero-at

# --- Row 1. CPU Thread Utilization (Utilization) ---------------------------------------------------------------
# The CPU threads in use on the running hosts, out of CPU Usable Capacity. A thread in use is the host's
# cpu.utilization % of its threads, so a busy small host counts less than a busy big one.
CPU = "Cluster-wide ESXi CPU Thread Utilization"
CPU_ROW = Metric(CPU, "%", 0.0, 55.0, 70.0, 85.0, 100.0)


def cpu_thread_utilization(usable: UsableCapacity, stats_by_host: StatsByHost) -> Optional[float]:
    threads_in_use = sum(stats_by_host[host.id][CPU_THREAD_UTIL] / 100.0 * host.threads for host in usable.cpu_hosts)
    return _consumed(threads_in_use, usable.cpu_threads)


# --- Row 2. Memory Consumed (Utilization) ------------------------------------------------------------------------
# The consumed memory of the running hosts, out of Memory Usable Capacity in DRAM.
MEMORY = "Cluster-wide ESXi Memory Consumed"
MEMORY_ROW = Metric(MEMORY, "%", 0.0, 70.0, 80.0, 90.0, 100.0)


def memory_consumed(usable: UsableCapacity, stats_by_host: StatsByHost) -> Optional[float]:
    return _consumed(_add_up(usable.dram_hosts, stats_by_host, [MEM_CONSUMED]), usable.dram_kb)


# --- Row 3. Memory Tiering Consumption (Saturation) --------------------------------------------------------------
# The NVMe memory tier in use on the running hosts, out of Memory Usable Capacity in NVMe tier. A cluster with no
# tier has no value. VCF Operations reports the usage in MB and the tier size in KB.
TIERING = "Cluster Memory Tiering Consumption"
TIERING_ROW = Metric(TIERING, "%", 0.0, 4.0, 8.0, 16.0, 32.0)


def memory_tiering_consumption(usable: UsableCapacity, tier_stats_by_host: StatsByHost) -> Optional[float]:
    used_mb = _add_up(usable.nvme_tier_hosts, tier_stats_by_host, [NVME_TIER_USAGE])
    return _consumed(None if used_mb is None else used_mb * 1024.0, usable.nvme_tier_kb)


# --- Row 4. Memory Ballooned (Saturation) ------------------------------------------------------------------------
# The ballooned memory of the running hosts, out of Memory Usable Capacity in DRAM.
BALLOONED = "Cluster-wide ESXi Memory Ballooned"
BALLOONED_ROW = Metric(BALLOONED, "%", 0.0, 1.0, 2.0, 4.0, 8.0)


def memory_ballooned(usable: UsableCapacity, stats_by_host: StatsByHost) -> Optional[float]:
    return _consumed(_add_up(usable.dram_hosts, stats_by_host, [MEM_BALLOONED]), usable.dram_kb)


# --- Row 5. Memory Zip Swap (Saturation) -------------------------------------------------------------------------
# The compressed plus swapped memory of the running hosts, out of Memory Usable Capacity in DRAM.
ZIP_SWAP = "Cluster-wide ESXi Memory Zip Swap"
ZIP_SWAP_ROW = Metric(ZIP_SWAP, "%", 0.0, 0.25, 0.5, 1.0, 2.0)


def memory_zip_swap(usable: UsableCapacity, stats_by_host: StatsByHost) -> Optional[float]:
    return _consumed(_add_up(usable.dram_hosts, stats_by_host, [MEM_COMPRESSED, MEM_SWAPPED]), usable.dram_kb)


# The rows, in the order of the source table. Every row is published on the cluster: none exists there already.
METRICS = [CPU_ROW, MEMORY_ROW, TIERING_ROW, BALLOONED_ROW, ZIP_SWAP_ROW]
PUBLISHED_METRICS = METRICS


# =================================================================================================================
# Part 3. The KPI
# =================================================================================================================

def consumption_values(hosts: List[HostInfo], stats_by_host: StatsByHost, tier_stats_by_host: StatsByHost,
                       cluster_stats: Dict[str, float]) -> Dict[str, Optional[float]]:
    """The value of every row for one cluster. None means "no data"."""
    usable = usable_capacity(hosts, stats_by_host, tier_stats_by_host, cluster_stats)
    return {
        CPU: cpu_thread_utilization(usable, stats_by_host),
        MEMORY: memory_consumed(usable, stats_by_host),
        TIERING: memory_tiering_consumption(usable, tier_stats_by_host),
        BALLOONED: memory_ballooned(usable, stats_by_host),
        ZIP_SWAP: memory_zip_swap(usable, stats_by_host),
    }


def collect_cluster_consumption_metrics(
    cluster_obj: Object, cluster_name: str, hosts: List[HostInfo],
    stats_by_host: StatsByHost, tier_stats_by_host: StatsByHost, cluster_stats: Dict[str, float],
) -> None:
    """Publishes the rows, then the Cluster Consumption KPI computed from them.

    hosts are the ESXi hosts of the cluster, stats_by_host the host stats Cluster Risk read this cycle
    ({host id: {stat key: value}}, empty when that read failed), tier_stats_by_host the HOST_STATS of the
    hosts, and cluster_stats the CLUSTER_STATS of this cluster.
    """
    try:
        for resource, usable_key, total_key in (("CPU", CPU_USABLE, CPU_TOTAL), ("memory", MEM_USABLE, MEM_TOTAL)):
            if not usable_percent(cluster_stats, usable_key, total_key):
                logger.info(f"Cluster Consumption for {cluster_name}: no {resource} Usable Capacity "
                            f"({usable_key} = {cluster_stats.get(usable_key)}, "
                            f"{total_key} = {cluster_stats.get(total_key)})")
        values = consumption_values(hosts, stats_by_host, tier_stats_by_host, cluster_stats)

        if not any(host_is_running(host, stats_by_host) for host in hosts):
            # No host runs (all down, powered off, in maintenance mode or disconnected): no VM runs, so nothing is
            # consumed. Not full: no data, whatever VCF Operations reports as Usable Capacity.
            logger.info(f"Cluster Consumption for {cluster_name}: no host runs, so no data")
            return

        if has_no_usable_capacity(cluster_stats):
            # Hosts run, but HA and the Buffer leave nothing to VMs: the VMs that run consume capacity that is not
            # usable, so the cluster is full, whatever the rows say. Publish the rows that still have a value
            # (metrics=[] scores nothing), then the KPI at 100: fully consumed.
            publish_kpi(cluster_obj, GROUP, KPI_KEY, [], PUBLISHED_METRICS, values, higher_is_worse=HIGHER_IS_WORSE)
            cluster_obj.with_metric(f"vCommunity|{GROUP}|{KPI_KEY}", FULL)
            logger.info(f"Cluster Consumption for {cluster_name}: no Usable Capacity, so {FULL} (fully consumed)")
            return

        no_data = publish_kpi(cluster_obj, GROUP, KPI_KEY, METRICS, PUBLISHED_METRICS, values,
                              higher_is_worse=HIGHER_IS_WORSE).no_data
        if no_data:
            logger.info(f"Cluster Consumption for {cluster_name}: no data, so left out: {', '.join(no_data)}")
    except Exception as e:
        # A failure here must not stop the collection of the other cluster data.
        logger.warning(f"Failed to calculate vSphere Cluster Consumption metrics for : {cluster_name} - {repr(e)}")
