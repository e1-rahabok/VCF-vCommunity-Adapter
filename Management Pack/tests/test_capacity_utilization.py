#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Capacity Utilization: sum of the host % / (N - k).

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.cluster import capacity_utilization as cu
from metrics.cluster import cluster_risk_metrics as cr
from utils.ops_inventory import ClusterHa
from fakes import FakeObject

GB_KB = 1024.0 * 1024.0


def host(cpu, consumed_gb, dram_gb=512.0):
    return {cr.CPU_THREAD_UTIL: cpu, cr.MEM_CONSUMED: consumed_gb * GB_KB, cr.MEM_DRAM_CAPACITY: dram_gb * GB_KB}


def test_n_plus_1_divides_by_n_minus_1():
    # 4 hosts at 60 % CPU, N+1: 240 / 3 = 80 %.
    assert cu.cluster_utilization([60.0] * 4, ClusterHa(4, 1)) == 80.0


def test_can_be_above_100_percent():
    # 4 hosts at 90 %, N+1: 360 / 3 = 120 %. The other three cannot hold the load after a host failure.
    assert cu.cluster_utilization([90.0] * 4, ClusterHa(4, 1)) == 120.0


def test_no_failover_level_counts_as_n_plus_0():
    assert cu.cluster_utilization([60.0] * 4, ClusterHa(4, None)) == 60.0


def test_a_host_without_data_gives_no_value():
    assert cu.cluster_utilization([60.0, None, 60.0], ClusterHa(3, 1)) is None
    # VCF Operations counts 4 hosts, only 3 found.
    assert cu.cluster_utilization([60.0] * 3, ClusterHa(4, 1)) is None


def test_no_usable_host_gives_no_value():
    assert cu.cluster_utilization([60.0], ClusterHa(1, 1)) is None


def test_memory_is_consumed_against_dram():
    # Consumed 256 GB of 512 GB = 50 % per host. 2 hosts, N+1: 100 / 1 = 100 %.
    stats = {"h1": host(40.0, 256.0), "h2": host(20.0, 256.0)}
    values = cu.utilization_values(["h1", "h2"], stats, ClusterHa(2, 1))
    assert values == {cu.CPU: 60.0, cu.MEMORY: 100.0}


def test_publish():
    cluster = FakeObject("cluster-a")
    cu.publish(cluster, {cu.CPU: 80.004, cu.MEMORY: None})
    assert cluster.metrics == {"vCommunity|Capacity|CPU Utilization": 80.0}
