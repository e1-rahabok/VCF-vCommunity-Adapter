#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Capacity Utilization: sum of the running hosts' % / (N - max(k, gone)).

The scenario table in docs/explanation/metrics/capacity-utilization.md is checked here, one test per row.
Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.cluster import capacity_utilization as cu
from metrics.cluster import cluster_risk_metrics as cr
from utils.ops_inventory import ClusterHa, HostInfo
from fakes import FakeObject

GB_KB = 1024.0 * 1024.0
N_PLUS_1 = ClusterHa(4, 1)


def host(name, connection="connected", power="Powered On", maintenance="notInMaintenance"):
    return HostInfo(name, name, name, "cluster-a", 32.0, 64.0, connection, maintenance, power)


HEALTHY = [host("h1"), host("h2"), host("h3"), host("h4")]


def test_all_running_and_full_is_133_percent():
    assert round(cu.cluster_utilization(HEALTHY, [100.0] * 4, N_PLUS_1), 2) == 133.33


def test_can_be_above_100_percent():
    # 4 hosts at 90 %, N+1: 360 / 3 = 120 %. The other three cannot hold the load after a host failure.
    assert cu.cluster_utilization(HEALTHY, [90.0] * 4, N_PLUS_1) == 120.0


def test_one_gone_host_uses_the_ha_spare():
    # Each way a host can be gone: 300 / (4 - max(1, 1)) = 100 %.
    gone_hosts = [
        host("h1", connection="notResponding"),                 # dead
        host("h1", connection="disconnected"),                  # disconnected
        host("h1", power="Powered Off"),                        # powered off
        host("h1", power="standBy"),                            # DPM standby
        host("h1", maintenance="inMaintenance"),                # in maintenance mode
    ]
    for gone in gone_hosts:
        assert cu.cluster_utilization([gone] + HEALTHY[1:], [100.0] * 4, N_PLUS_1) == 100.0, gone
    # No current value (none, or stale and dropped): also gone.
    assert cu.cluster_utilization(HEALTHY, [None, 100.0, 100.0, 100.0], N_PLUS_1) == 100.0


def test_entering_maintenance_mode_still_counts():
    hosts = [host("h1", maintenance="enteringMaintenance")] + HEALTHY[1:]
    assert round(cu.cluster_utilization(hosts, [100.0] * 4, N_PLUS_1), 2) == 133.33


def test_more_gone_hosts_than_ha_covers_takes_capacity_away():
    hosts = [host("h1", connection="notResponding"), host("h2", power="Powered Off")] + HEALTHY[2:]
    # 200 / (4 - max(1, 2)) = 100 %, and 160 / 2 = 80 %.
    assert cu.cluster_utilization(hosts, [None, None, 100.0, 100.0], N_PLUS_1) == 100.0
    assert cu.cluster_utilization(hosts, [None, None, 80.0, 80.0], N_PLUS_1) == 80.0


def test_a_host_counted_but_not_found_is_gone():
    # VCF Operations counts 4 hosts, only 3 found: 300 / 3 = 100 %.
    assert cu.cluster_utilization(HEALTHY[:3], [100.0] * 3, N_PLUS_1) == 100.0


def test_no_failover_level_counts_as_n_plus_0():
    assert cu.cluster_utilization(HEALTHY, [60.0] * 4, ClusterHa(4, None)) == 60.0


def test_no_capacity_left_gives_no_value():
    assert cu.cluster_utilization([host("h1")], [60.0], ClusterHa(1, 1)) is None
    assert cu.cluster_utilization(HEALTHY, [None] * 4, N_PLUS_1) is None


def test_memory_is_consumed_against_dram():
    # Consumed 256 GB of 512 GB = 50 % per host. 2 hosts, N+1: 100 / 1 = 100 %.
    def stats(cpu):
        return {cr.CPU_THREAD_UTIL: cpu, cr.MEM_CONSUMED: 256.0 * GB_KB, cr.MEM_DRAM_CAPACITY: 512.0 * GB_KB}
    values = cu.utilization_values([host("h1"), host("h2")], {"h1": stats(40.0), "h2": stats(20.0)}, ClusterHa(2, 1))
    assert values == {cu.CPU: 60.0, cu.MEMORY: 100.0}


def test_publish():
    cluster = FakeObject("cluster-a")
    cu.publish(cluster, {cu.CPU: 80.004, cu.MEMORY: None})
    assert cluster.metrics == {"vCommunity|Capacity|CPU Utilization": 80.0}


def test_a_missing_value_is_explained_in_the_log(caplog):
    import logging
    caplog.set_level(logging.INFO)
    hosts = [host("h1", connection="notResponding")] + HEALTHY[1:]
    cu.utilization_values(hosts, {}, N_PLUS_1, "cluster-a")
    assert "Capacity CPU Utilization of cluster-a: no value" in caplog.text
    assert "h1: no current value" in caplog.text
    assert "N=4" in caplog.text and "k=1" in caplog.text
