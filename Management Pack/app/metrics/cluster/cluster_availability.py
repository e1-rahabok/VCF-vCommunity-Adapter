#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Operational Availability (%, per cluster).

min(100, (sum of the host values - the k lowest host values) / (N - k))
N is the number of hosts in the cluster, k the number of host failures vSphere HA tolerates (N+k). The k spare hosts
are assumed to be the k worst hosts, so any other degraded host counts against the cluster. Capped at 100 %, so a
cluster with more spare capacity does not look better. No value when N - k is 0 or less.

N is summary|total_number_hosts. When VCF Operations has no value, the hosts found in the cluster. No host failover
level (HA off, percentage-based or dedicated-host admission control, or the value was not collected) counts as k = 0.
That makes the value lower than real, never higher.

All inputs come from VCF Operations. See docs/reference/metrics/operational-availability.md, including its known limitations.
"""
from typing import Dict, List, Optional
from aria.ops.suite_api_client import SuiteApiClient
from metrics.host.host_availability import GROUP
from utils import ops_inventory
from utils.ops_inventory import HostInfo

CLUSTER_METRIC = "Cluster Operational Availability"


def cluster_availability(host_values: List[float], host_count: Optional[float],
                         failover_level: Optional[float]) -> Optional[float]:
    """min(100, (sum - the k lowest) / (N - k)). None when N - k is 0 or less.

    host_values has one value per host found in the cluster. Hosts counted in host_count but not found
    count as 0 %. No failover level counts as k = 0.
    """
    n = max(int(host_count or 0), len(host_values))
    k = int(failover_level or 0)
    if n - k <= 0:
        return None
    # A host that VCF Operations counts but that has no data is unavailable: 0 %.
    values = sorted(host_values + [0.0] * (n - len(host_values)))
    return min(100.0, (sum(values) - sum(values[:k])) / (n - k))


def read_cluster_availability(suite_api_client: SuiteApiClient, clusters, hosts: List[HostInfo],
                              by_host: Dict[str, float]) -> Dict[str, Optional[float]]:
    """{cluster name: %}."""
    ha_by_cluster = ops_inventory.read_cluster_ha(suite_api_client, clusters)
    by_cluster = {}
    for cluster in clusters:
        ha = ha_by_cluster[cluster.name]
        host_values = [by_host[host.id] for host in hosts if host.cluster_name == cluster.name]
        by_cluster[cluster.name] = cluster_availability(host_values, ha.host_count, ha.failover_level)
    return by_cluster


def publish(obj, value: Optional[float]) -> None:
    """Publishes the cluster value under vCommunity|Availability, rounded to two decimals."""
    if value is not None:
        obj.with_metric(f"vCommunity|{GROUP}|{CLUSTER_METRIC}", round(value, 2))
