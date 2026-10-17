#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Worked examples for the Cluster Consumption KPI. They double as documentation.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.cluster import cluster_consumption_metrics as cc
from metrics.cluster import cluster_risk_metrics as cr
from utils.ops_inventory import HostInfo
from fakes import FakeObject

GB_IN_KB = 1024.0 * 1024.0


def host(host_id, cores, maintenance_state="notInMaintenance"):
    """A connected, powered-on host with hyper-threading: twice as many threads as cores."""
    return HostInfo(host_id, host_id, host_id, "cluster-1", cores, cores * 2,
                    "connected", maintenance_state, "Powered On")


def host_stats(cpu_util, dram_gb, consumed_gb, ballooned_gb=0.0, compressed_gb=0.0, swapped_gb=0.0):
    """The latest stats of one host, as Cluster Risk reads them (memory in KB)."""
    return {
        cr.CPU_THREAD_UTIL: cpu_util,
        cr.MEM_DRAM_CAPACITY: dram_gb * GB_IN_KB,
        cr.MEM_CONSUMED: consumed_gb * GB_IN_KB,
        cr.MEM_BALLOONED: ballooned_gb * GB_IN_KB,
        cr.MEM_COMPRESSED: compressed_gb * GB_IN_KB,
        cr.MEM_SWAPPED: swapped_gb * GB_IN_KB,
    }


# A big host (32 cores, 64 threads, 512 GB) and a small one (16 cores, 32 threads, 256 GB).
HOSTS = [host("host-1", 32.0), host("host-2", 16.0)]
STATS = {
    "host-1": host_stats(cpu_util=40.0, dram_gb=512.0, consumed_gb=256.0, ballooned_gb=5.12),
    "host-2": host_stats(cpu_util=70.0, dram_gb=256.0, consumed_gb=230.4),
}


def test_limits_match_the_source_table():
    # docs/reference/metrics/formula/cluster-consumption.png
    limits = {m.name: (m.best, m.green, m.yellow, m.orange, m.zero_at, m.skip_when_green) for m in cc.METRICS}
    assert limits == {
        "Cluster-wide ESXi CPU Thread Utilization": (0, 55, 70, 85, 100, False),
        "Cluster-wide ESXi Memory Consumed": (0, 70, 80, 90, 100, False),
        "Cluster Memory Tiering Consumption": (0, 4, 8, 16, 32, False),
        "Cluster-wide ESXi Memory Ballooned": (0, 1, 2, 4, 8, False),
        "Cluster-wide ESXi Memory Zip Swap": (0, 0.25, 0.5, 1, 2, False),
    }


def test_cluster_wide_means_the_hosts_added_up_not_averaged():
    values = cc.consumption_values(HOSTS, STATS, {})
    # CPU: 40 % of 64 threads + 70 % of 32 threads = 25.6 + 22.4 = 48 of 96 threads = 50 %.
    # The average of 40 and 70 would be 55: the small host would count as much as the big one.
    assert values[cc.CPU] == 50.0
    # Memory: (256 + 230.4) GB of (512 + 256) GB = 63.33 %.
    assert round(values[cc.MEMORY], 2) == 63.33
    # Ballooned: 5.12 GB of 768 GB = 0.67 %.
    assert round(values[cc.BALLOONED], 2) == 0.67
    assert values[cc.ZIP_SWAP] == 0.0
    # No NVMe memory tiering: no data.
    assert values[cc.TIERING] is None


def test_zip_swap_adds_compressed_and_swapped():
    stats = {"host-1": host_stats(40.0, 512.0, 256.0, compressed_gb=1.0, swapped_gb=0.92),
             "host-2": host_stats(70.0, 256.0, 128.0)}
    # (1 + 0.92) GB of 768 GB = 0.25 %.
    assert round(cc.consumption_values(HOSTS, stats, {})[cc.ZIP_SWAP], 2) == 0.25


def test_memory_tiering_consumption_is_the_cluster_stat():
    values = cc.consumption_values(HOSTS, STATS, {cc.MEM_TIERING_USAGE: 6.0})
    assert values[cc.TIERING] == 6.0


def test_a_host_in_maintenance_mode_is_left_out():
    # Its CPU and memory would otherwise add free capacity that no VM can use.
    hosts = HOSTS + [host("host-3", 32.0, maintenance_state="inMaintenance")]
    stats = {**STATS, "host-3": host_stats(cpu_util=0.0, dram_gb=512.0, consumed_gb=0.0)}
    assert cc.consumption_values(hosts, stats, {}) == cc.consumption_values(HOSTS, STATS, {})


def test_a_host_without_data_is_left_out():
    stats = {"host-1": STATS["host-1"]}
    values = cc.consumption_values(HOSTS, stats, {})
    assert values[cc.CPU] == 40.0
    assert values[cc.MEMORY] == 50.0


def test_no_host_data_at_all():
    values = cc.consumption_values(HOSTS, {}, {})
    assert values == {cc.CPU: None, cc.MEMORY: None, cc.TIERING: None, cc.BALLOONED: None, cc.ZIP_SWAP: None}


def test_the_kpi():
    cluster = FakeObject("cluster-1")
    cc.collect_cluster_consumption_metrics(cluster, "Cluster 1", HOSTS, STATS, {})
    published = {key.split("|")[-1]: value for key, value in cluster.metrics.items()}
    # All four rows with data are green, each with weight 1:
    #   CPU 50          100 - 50 / 55 x 25     = 77.27
    #   Memory 63.33    100 - 63.33 / 70 x 25  = 77.38
    #   Ballooned 0.67  100 - 0.67 / 1 x 25    = 83.25
    #   Zip Swap 0      100
    # Score = 337.90 / 4 = 84.48. Consumption is higher-is-worse: 100 - 84.48 = 15.52.
    assert published[cc.CPU] == 50.0
    assert cc.TIERING not in published
    assert published[cc.KPI_KEY] == 15.52
    assert cc.HIGHER_IS_WORSE


def test_a_full_cluster_is_red():
    stats = {"host-1": host_stats(95.0, 512.0, 500.0, ballooned_gb=40.0),
             "host-2": host_stats(95.0, 256.0, 250.0, ballooned_gb=20.0)}
    cluster = FakeObject("cluster-1")
    cc.collect_cluster_consumption_metrics(cluster, "Cluster 1", HOSTS, stats, {})
    assert cluster.metrics[f"vCommunity|{cc.GROUP}|{cc.KPI_KEY}"] > 75.0
