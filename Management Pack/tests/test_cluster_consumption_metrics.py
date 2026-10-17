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


def cluster(usable_fraction):
    """The usable capacity of the cluster as VCF Operations reports it: Total - HA - Buffer."""
    return {cc.CPU_TOTAL: 100000.0, cc.CPU_USABLE: 100000.0 * usable_fraction,
            cc.MEM_TOTAL: 1000.0 * GB_IN_KB, cc.MEM_USABLE: 1000.0 * GB_IN_KB * usable_fraction}


# A big host (32 cores, 64 threads, 512 GB) and a small one (16 cores, 32 threads, 256 GB).
HOSTS = [host("host-1", 32.0), host("host-2", 16.0)]
STATS = {
    "host-1": host_stats(cpu_util=40.0, dram_gb=512.0, consumed_gb=256.0, ballooned_gb=5.12),
    "host-2": host_stats(cpu_util=70.0, dram_gb=256.0, consumed_gb=230.4),
}
NO_HA_NO_BUFFER = cluster(1.0)
HA_AND_BUFFER = cluster(0.8)        # HA and the capacity buffer take 20 % of the total


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
    values = cc.consumption_values(HOSTS, STATS, {}, NO_HA_NO_BUFFER)
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


def test_consumption_is_against_usable_capacity():
    # HA and the buffer take 20 %: usable is 80 % of the total, so the same load is a larger share.
    values = cc.consumption_values(HOSTS, STATS, {}, HA_AND_BUFFER)
    assert round(values[cc.CPU], 2) == 62.5             # 48 of 96 x 0.8 = 76.8 threads
    assert round(values[cc.MEMORY], 2) == 79.17         # 486.4 GB of 768 x 0.8 = 614.4 GB
    assert round(values[cc.BALLOONED], 2) == 0.83       # 5.12 GB of 614.4 GB


def test_cpu_and_memory_have_their_own_usable_fraction():
    stats = {**cluster(1.0), cc.CPU_USABLE: 50000.0}     # CPU half usable, memory fully
    values = cc.consumption_values(HOSTS, STATS, {}, stats)
    assert values[cc.CPU] == 100.0
    assert round(values[cc.MEMORY], 2) == 63.33


def test_zip_swap_adds_compressed_and_swapped():
    stats = {"host-1": host_stats(40.0, 512.0, 256.0, compressed_gb=1.0, swapped_gb=0.92),
             "host-2": host_stats(70.0, 256.0, 128.0)}
    # (1 + 0.92) GB of 768 GB = 0.25 %.
    assert round(cc.consumption_values(HOSTS, stats, {}, NO_HA_NO_BUFFER)[cc.ZIP_SWAP], 2) == 0.25


def test_memory_tiering_is_against_the_usable_nvme_tier_only():
    # host-1 has a 256 GB NVMe tier with 20 GB in use (VCF Operations reports the usage in MB). host-2 has none.
    tiers = {"host-1": {cc.NVME_TIER_SIZE: 256.0 * GB_IN_KB, cc.NVME_TIER_USAGE: 20.0 * 1024.0}}
    # 20 GB of 256 GB x 0.8 usable = 204.8 GB: 9.77 %. DRAM plays no part.
    assert round(cc.consumption_values(HOSTS, STATS, tiers, HA_AND_BUFFER)[cc.TIERING], 2) == 9.77
    # The DRAM rows do not change with a tier.
    assert cc.consumption_values(HOSTS, STATS, tiers, HA_AND_BUFFER)[cc.MEMORY] == \
        cc.consumption_values(HOSTS, STATS, {}, HA_AND_BUFFER)[cc.MEMORY]


def test_no_usable_capacity_is_no_data_not_full():
    # Seen on a live system: usable capacity reported as 0 for a while. Never divide by it.
    for stats in ({}, cluster(0.0), {**cluster(1.0), cc.MEM_TOTAL: 0.0}):
        values = cc.consumption_values(HOSTS, STATS, {}, stats)
        assert values[cc.MEMORY] is None
    assert cc.consumption_values(HOSTS, STATS, {}, cluster(0.0))[cc.CPU] is None


def test_a_host_in_maintenance_mode_is_left_out():
    # Its CPU and memory would otherwise add free capacity that no VM can use.
    hosts = HOSTS + [host("host-3", 32.0, maintenance_state="inMaintenance")]
    stats = {**STATS, "host-3": host_stats(cpu_util=0.0, dram_gb=512.0, consumed_gb=0.0)}
    assert cc.consumption_values(hosts, stats, {}, HA_AND_BUFFER) == cc.consumption_values(HOSTS, STATS, {}, HA_AND_BUFFER)


def test_a_host_without_data_is_left_out():
    values = cc.consumption_values(HOSTS, {"host-1": STATS["host-1"]}, {}, NO_HA_NO_BUFFER)
    assert values[cc.CPU] == 40.0
    assert values[cc.MEMORY] == 50.0


def test_the_kpi():
    obj = FakeObject("cluster-1")
    cc.collect_cluster_consumption_metrics(obj, "Cluster 1", HOSTS, STATS, {}, HA_AND_BUFFER)
    published = {key.split("|")[-1]: value for key, value in obj.metrics.items()}
    # Against usable capacity (80 % of the total):
    #   CPU 62.5        yellow  75 - (62.5 - 55) / 15 x 25    = 62.5    weight 2
    #   Memory 79.17    yellow  75 - (79.17 - 70) / 10 x 25   = 52.08   weight 2
    #   Ballooned 0.83  green   100 - 0.83 x 25               = 79.25   weight 1
    #   Zip Swap 0      green   100                                     weight 1
    # Score = (62.5 x 2 + 52.08 x 2 + 79.25 + 100) / 6 = 68.07. Consumption is higher-is-worse: 100 - 68.07 = 31.93.
    assert published[cc.CPU] == 62.5
    assert cc.TIERING not in published
    assert published[cc.KPI_KEY] == 31.93
    assert cc.HIGHER_IS_WORSE


def test_a_full_cluster_is_red():
    stats = {"host-1": host_stats(95.0, 512.0, 500.0, ballooned_gb=40.0),
             "host-2": host_stats(95.0, 256.0, 250.0, ballooned_gb=20.0)}
    obj = FakeObject("cluster-1")
    cc.collect_cluster_consumption_metrics(obj, "Cluster 1", HOSTS, stats, {}, HA_AND_BUFFER)
    assert obj.metrics[f"vCommunity|{cc.GROUP}|{cc.KPI_KEY}"] > 75.0


def test_no_usable_capacity_publishes_no_kpi():
    obj = FakeObject("cluster-1")
    cc.collect_cluster_consumption_metrics(obj, "Cluster 1", HOSTS, STATS, {}, cluster(0.0))
    assert obj.metrics == {}
