#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Consumption KPI.

What it is
----------
One 0-100 % score per vSphere cluster. 0 is nothing consumed, 100 is fully consumed: higher is worse, like
Cluster Risk. It measures actual utilization and saturation of the cluster as a whole, against its usable
capacity. It is built from the 5 sub-metrics in METRICS below.

Unlike Cluster Risk, every sub-metric is cluster-wide, not the worst ESXi host: the hosts are added up, so a
big host counts more than a small one. Saturation (ballooned, swapped and zipped memory) is not contention,
because nothing is slow yet. It is real consumption, so it is tracked with its own sub-metrics.

Published on the cluster as:
    vCommunity|Cluster Consumption|Cluster Consumption Score    the KPI
    vCommunity|Cluster Consumption|<sub-metric name>            each of the 5 sub-metrics

Usable capacity
---------------
Usable = Total - HA - Buffer. VCF Operations calculates it per cluster, from the cluster's HA admission
control and the capacity buffer (Demand) of its policy: CPU_USABLE and MEM_USABLE. Their share of the
cluster total (CPU_TOTAL, MEM_TOTAL) is the usable fraction, applied to what the hosts have:

    CPU Thread Utilization   threads in use / (all threads x CPU usable fraction)
    Memory Consumed          consumed / (DRAM x memory usable fraction)
    Memory Ballooned         ballooned / (DRAM x memory usable fraction)
    Memory Zip Swap          (compressed + swapped) / (DRAM x memory usable fraction)
    Memory Tiering           NVMe tier in use / (NVMe tier size x memory usable fraction)

All sums are over the running hosts of the cluster (capacity_utilization.host_is_gone). DRAM and the NVMe tier
are kept apart: the DRAM rows never include the tier, and the tier row never includes DRAM.

No usable capacity: when the cluster has CPU or memory but HA and the buffer leave none of it to VMs (usable = 0),
the cluster is full. The rows of that resource have no meaningful % and are not published, and the KPI is
published as FULL (100). A missing usable value is no data.

Host stats: the DRAM, CPU and memory stats are the ones Cluster Risk already read this cycle
(cluster_risk_metrics.HOST_STATS). The NVMe tier stats (HOST_STATS here) and the cluster stats (CLUSTER_STATS)
are read once per cycle for all hosts and clusters by the cluster collector.

Where the limits come from
--------------------------
docs/reference/metrics/formula/cluster-consumption.png. No green range is "Excluded".

Missing data
------------
A sub-metric with no data is not published and is left out of the KPI. A cluster without NVMe memory
tiering has no Memory Tiering Consumption, so that sub-metric is left out for it.

Called from: collectors/cluster/collectClusterData.py, once per cluster.
Used by the Periodic Cluster Check (periodic_cluster_check.py).
Description for people who do not read code: docs/reference/metrics/cluster-consumption.md
"""
import logging
from typing import Dict, List, Optional
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
# The KPI of a cluster with no usable capacity: fully consumed.
FULL = 100.0

CPU = "Cluster-wide ESXi CPU Thread Utilization"
MEMORY = "Cluster-wide ESXi Memory Consumed"
TIERING = "Cluster Memory Tiering Consumption"
BALLOONED = "Cluster-wide ESXi Memory Ballooned"
ZIP_SWAP = "Cluster-wide ESXi Memory Zip Swap"

# One row per sub-metric. The five numbers are the values where its score is 100, 75, 50, 25 and 0.
# Every sub-metric here is "lower is better", in % of the usable capacity.
METRICS = [
    #       name        unit   best  green  yellow  orange  zero-at

    # --- Utilization ---
    Metric(CPU,         "%",   0.0,  55.0,  70.0,   85.0,   100.0),
    Metric(MEMORY,      "%",   0.0,  70.0,  80.0,   90.0,   100.0),

    # --- Saturation ---
    Metric(TIERING,     "%",   0.0,  4.0,   8.0,    16.0,   32.0),
    Metric(BALLOONED,   "%",   0.0,  1.0,   2.0,    4.0,    8.0),
    Metric(ZIP_SWAP,    "%",   0.0,  0.25,  0.5,    1.0,    2.0),
]

# Every sub-metric is published on the cluster, because none of them exists there as a stat already.
PUBLISHED_METRICS = METRICS

# Cluster stats of VCF Operations. Usable is Total - HA - Buffer (Demand), in the same unit as its total.
CPU_USABLE = "cpu|demand|usableCapacity"            # MHz
CPU_TOTAL = "cpu|capacity_provisioned"              # MHz
MEM_USABLE = "mem|demand|usableCapacity"            # KB
MEM_TOTAL = "mem|host_provisioned"                  # KB
CLUSTER_STATS = [CPU_USABLE, CPU_TOTAL, MEM_USABLE, MEM_TOTAL]

# Host stats of the NVMe memory tier. Only hosts with memory tiering have them.
NVME_TIER_USAGE = "mem:NVMe|tier.usage"             # MB in use
NVME_TIER_SIZE = "mem:NVMe|memory_tier_size"        # KB
HOST_STATS = [NVME_TIER_USAGE, NVME_TIER_SIZE]


# ---------------------------------------------------------------------------
# Usable capacity.
# ---------------------------------------------------------------------------

def usable_fraction(cluster_stats: Dict[str, float], usable_key: str, total_key: str) -> Optional[float]:
    """Usable / total of one resource of the cluster, such as 0.8. None when either is missing, or the total is 0.

    0.0 is a real answer: the cluster has capacity, but HA and the buffer leave none of it to VMs, for example
    when HA tolerates one host failure and only one host runs. Such a cluster is full.
    """
    usable = cluster_stats.get(usable_key)
    total = cluster_stats.get(total_key)
    if usable is None or not total or total <= 0:
        return None
    return max(usable, 0.0) / total


def has_no_usable_capacity(cluster_stats: Dict[str, float]) -> bool:
    """True when the cluster has CPU or memory, but none of it is usable by VMs: it is full."""
    return any(usable_fraction(cluster_stats, usable, total) == 0.0
               for usable, total in ((CPU_USABLE, CPU_TOTAL), (MEM_USABLE, MEM_TOTAL)))


# ---------------------------------------------------------------------------
# Sub-metric formulas for the whole cluster. Each returns None when it has no data to work with.
# ---------------------------------------------------------------------------

def cpu_thread_utilization(
    hosts: List[HostInfo], stats_by_host: Dict[str, Dict[str, float]], cpu_fraction: Optional[float]
) -> Optional[float]:
    """CPU threads in use on the running hosts, as a share of their usable CPU threads."""
    if not cpu_fraction:
        return None
    threads_in_use = 0.0
    threads = 0.0
    for host in hosts:
        utilization = stats_by_host.get(host.id, {}).get(CPU_THREAD_UTIL)
        if host_is_gone(host, utilization) or not host.threads:
            continue
        threads_in_use += utilization / 100.0 * host.threads
        threads += host.threads
    return percent(threads_in_use, threads * cpu_fraction) if threads else None


def dram_share(
    hosts: List[HostInfo], stats_by_host: Dict[str, Dict[str, float]], stat_keys: List[str],
    memory_fraction: Optional[float],
) -> Optional[float]:
    """The stats in stat_keys, added up over the running hosts, as a share of their usable DRAM.

    A host counts only when it has all of stat_keys and its DRAM. Several keys, such as compressed and
    swapped, are added per host first.
    """
    if not memory_fraction:
        return None
    memory_kb = 0.0
    dram_kb = 0.0
    for host in hosts:
        stats = stats_by_host.get(host.id, {})
        host_dram_kb = dram_capacity_kb(stats)
        values = [stats.get(key) for key in stat_keys]
        amount = None if None in values or host_dram_kb is None else sum(values)
        if host_is_gone(host, amount):
            continue
        memory_kb += amount
        dram_kb += host_dram_kb
    return percent(memory_kb, dram_kb * memory_fraction) if dram_kb else None


def tiering_share(
    hosts: List[HostInfo], tier_stats_by_host: Dict[str, Dict[str, float]], memory_fraction: Optional[float]
) -> Optional[float]:
    """NVMe tier in use on the running hosts, as a share of their usable NVMe tier. None without a tier."""
    if not memory_fraction:
        return None
    used_kb = 0.0
    size_kb = 0.0
    for host in hosts:
        stats = tier_stats_by_host.get(host.id, {})
        host_size_kb = stats.get(NVME_TIER_SIZE)
        used_mb = stats.get(NVME_TIER_USAGE)
        if not host_size_kb or host_is_gone(host, used_mb):
            continue
        used_kb += used_mb * 1024.0
        size_kb += host_size_kb
    return percent(used_kb, size_kb * memory_fraction) if size_kb else None


def consumption_values(
    hosts: List[HostInfo], stats_by_host: Dict[str, Dict[str, float]],
    tier_stats_by_host: Dict[str, Dict[str, float]], cluster_stats: Dict[str, float],
) -> Dict[str, Optional[float]]:
    """The value of every sub-metric in METRICS for one cluster. None means "no data"."""
    cpu_fraction = usable_fraction(cluster_stats, CPU_USABLE, CPU_TOTAL)
    memory_fraction = usable_fraction(cluster_stats, MEM_USABLE, MEM_TOTAL)
    return {
        CPU: cpu_thread_utilization(hosts, stats_by_host, cpu_fraction),
        MEMORY: dram_share(hosts, stats_by_host, [MEM_CONSUMED], memory_fraction),
        TIERING: tiering_share(hosts, tier_stats_by_host, memory_fraction),
        BALLOONED: dram_share(hosts, stats_by_host, [MEM_BALLOONED], memory_fraction),
        ZIP_SWAP: dram_share(hosts, stats_by_host, [MEM_COMPRESSED, MEM_SWAPPED], memory_fraction),
    }


# ---------------------------------------------------------------------------
# Entry point, called once per cluster.
# ---------------------------------------------------------------------------

def collect_cluster_consumption_metrics(
    cluster_obj: Object, cluster_name: str, hosts: List[HostInfo],
    stats_by_host: Dict[str, Dict[str, float]], tier_stats_by_host: Dict[str, Dict[str, float]],
    cluster_stats: Dict[str, float],
) -> None:
    """Publishes the sub-metrics in METRICS, then the Cluster Consumption KPI computed from them.

    hosts are the ESXi hosts of the cluster, stats_by_host the host stats Cluster Risk read this cycle
    ({host id: {stat key: value}}, empty when that read failed), tier_stats_by_host the HOST_STATS of the
    hosts, and cluster_stats the CLUSTER_STATS of this cluster.
    """
    try:
        for name, usable, total in (("CPU", CPU_USABLE, CPU_TOTAL), ("memory", MEM_USABLE, MEM_TOTAL)):
            if not usable_fraction(cluster_stats, usable, total):
                logger.info(f"Cluster Consumption for {cluster_name}: no usable {name} capacity "
                            f"({usable} = {cluster_stats.get(usable)}, {total} = {cluster_stats.get(total)})")
        values = consumption_values(hosts, stats_by_host, tier_stats_by_host, cluster_stats)

        if has_no_usable_capacity(cluster_stats):
            # HA and the buffer leave nothing to VMs: the cluster is full, whatever the rows say. Publish the rows
            # that still have a value (metrics=[] scores nothing), then the KPI at 100: fully consumed.
            publish_kpi(cluster_obj, GROUP, KPI_KEY, [], PUBLISHED_METRICS, values, higher_is_worse=HIGHER_IS_WORSE)
            cluster_obj.with_metric(f"vCommunity|{GROUP}|{KPI_KEY}", FULL)
            logger.info(f"Cluster Consumption for {cluster_name}: no usable capacity, so {FULL} (fully consumed)")
            return

        no_data = publish_kpi(cluster_obj, GROUP, KPI_KEY, METRICS, PUBLISHED_METRICS, values,
                              higher_is_worse=HIGHER_IS_WORSE).no_data
        if no_data:
            logger.info(f"Cluster Consumption for {cluster_name}: no data, so left out: {', '.join(no_data)}")
    except Exception as e:
        # A failure here must not stop the collection of the other cluster data.
        logger.warning(f"Failed to calculate vSphere Cluster Consumption metrics for : {cluster_name} - {repr(e)}")
