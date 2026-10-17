#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Consumption KPI.

What it is
----------
One 0-100 % score per vSphere cluster. 0 is nothing consumed, 100 is fully consumed: higher is worse, like
Cluster Risk. It measures actual utilization and saturation of the cluster as a whole. It is built from the
5 sub-metrics in METRICS below.

Unlike Cluster Risk, every sub-metric is cluster-wide, not the worst ESXi host: the hosts are added up, so a
big host counts more than a small one. Saturation (ballooned, swapped and zipped memory) is not contention,
because nothing is slow yet. It is real consumption, so it is tracked with its own sub-metrics.

Published on the cluster as:
    vCommunity|Cluster Consumption|Cluster Consumption Score    the KPI
    vCommunity|Cluster Consumption|<sub-metric name>            each of the 5 sub-metrics

How it is calculated
--------------------
1. Take the running hosts of the cluster (capacity_utilization.host_is_gone) and the host stats that Cluster
   Risk already read this cycle (cluster_risk_metrics.HOST_STATS), so nothing is read twice.
2. Add them up: the CPU threads in use against all CPU threads, and each memory amount against all DRAM.
   Memory Tiering Consumption is a cluster stat of VCF Operations, read as it is.
3. Score each value and combine the scores, as for every KPI (metrics/kpi_score.py). The published Cluster
   Consumption is 100 minus that score (HIGHER_IS_WORSE).

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

CPU = "Cluster-wide ESXi CPU Thread Utilization"
MEMORY = "Cluster-wide ESXi Memory Consumed"
TIERING = "Cluster Memory Tiering Consumption"
BALLOONED = "Cluster-wide ESXi Memory Ballooned"
ZIP_SWAP = "Cluster-wide ESXi Memory Zip Swap"

# One row per sub-metric. The five numbers are the values where its score is 100, 75, 50, 25 and 0.
# Every sub-metric here is "lower is better".
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
# Memory Tiering Consumption does, but under its own key; publishing it here keeps the KPI's inputs together.
PUBLISHED_METRICS = METRICS

# The cluster stat of VCF Operations behind Memory Tiering Consumption (%). Only clusters with NVMe memory
# tiering have it.
MEM_TIERING_USAGE = "mem|tier_1_usage_percent"
CLUSTER_STATS = [MEM_TIERING_USAGE]


# ---------------------------------------------------------------------------
# Sub-metric formulas for the whole cluster. Each returns None when it has no data to work with.
# ---------------------------------------------------------------------------

def cpu_thread_utilization(hosts: List[HostInfo], stats_by_host: Dict[str, Dict[str, float]]) -> Optional[float]:
    """CPU threads in use on the running hosts, as a share of all their CPU threads."""
    threads_in_use = 0.0
    threads = 0.0
    for host in hosts:
        utilization = stats_by_host.get(host.id, {}).get(CPU_THREAD_UTIL)
        if host_is_gone(host, utilization) or not host.threads:
            continue
        threads_in_use += utilization / 100.0 * host.threads
        threads += host.threads
    return percent(threads_in_use, threads) if threads else None


def memory_share(hosts: List[HostInfo], stats_by_host: Dict[str, Dict[str, float]], stat_keys: List[str]) -> Optional[float]:
    """The stats in stat_keys, added up over the running hosts, as a share of their DRAM.

    A host counts only when it has all of stat_keys and its DRAM. Several keys, such as compressed and
    swapped, are added per host first.
    """
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
    return percent(memory_kb, dram_kb) if dram_kb else None


def consumption_values(
    hosts: List[HostInfo], stats_by_host: Dict[str, Dict[str, float]], cluster_stats: Dict[str, float]
) -> Dict[str, Optional[float]]:
    """The value of every sub-metric in METRICS for one cluster. None means "no data"."""
    return {
        CPU: cpu_thread_utilization(hosts, stats_by_host),
        MEMORY: memory_share(hosts, stats_by_host, [MEM_CONSUMED]),
        TIERING: cluster_stats.get(MEM_TIERING_USAGE),
        BALLOONED: memory_share(hosts, stats_by_host, [MEM_BALLOONED]),
        ZIP_SWAP: memory_share(hosts, stats_by_host, [MEM_COMPRESSED, MEM_SWAPPED]),
    }


# ---------------------------------------------------------------------------
# Entry point, called once per cluster.
# ---------------------------------------------------------------------------

def collect_cluster_consumption_metrics(
    cluster_obj: Object, cluster_name: str, hosts: List[HostInfo],
    stats_by_host: Dict[str, Dict[str, float]], cluster_stats: Dict[str, float],
) -> None:
    """Publishes the sub-metrics in METRICS, then the Cluster Consumption KPI computed from them.

    hosts are the ESXi hosts of the cluster, stats_by_host the host stats Cluster Risk read this cycle
    ({host id: {stat key: value}}, empty when that read failed), and cluster_stats the CLUSTER_STATS of
    this cluster.
    """
    try:
        values = consumption_values(hosts, stats_by_host, cluster_stats)
        no_data = publish_kpi(cluster_obj, GROUP, KPI_KEY, METRICS, PUBLISHED_METRICS, values,
                              higher_is_worse=HIGHER_IS_WORSE).no_data
        if no_data:
            logger.info(f"Cluster Consumption for {cluster_name}: no data, so left out: {', '.join(no_data)}")
    except Exception as e:
        # A failure here must not stop the collection of the other cluster data.
        logger.warning(f"Failed to calculate vSphere Cluster Consumption metrics for : {cluster_name} - {repr(e)}")
