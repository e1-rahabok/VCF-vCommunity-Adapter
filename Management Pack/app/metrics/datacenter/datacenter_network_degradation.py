#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Total Network Speed Degradation per Datacenter: the number of its hosts below 100 %.

The hosts are those of this account's vCenter, matched to the Datacenter by name (summary|parentDatacenter). A
Datacenter is in one vCenter, so the count is from the same collection cycle. A host without a value is not counted.

All inputs come from VCF Operations. See docs/reference/metrics/network-speed-degradation.md, including its known limitations.
"""
from typing import Dict, List, Optional
from aria.ops.suite_api_client import SuiteApiClient
from metrics.host.host_network_speed import GROUP, degraded_count
from utils.ops_stats import read_latest_properties

COUNT_METRIC = "Total Network Speed Degradation"
HOST_DATACENTER = "summary|parentDatacenter"        # name of the Datacenter the host is in


def read_count_by_datacenter(suite_api_client: SuiteApiClient, host_ids: List[str],
                             by_host: Dict[str, Optional[float]]) -> Dict[str, int]:
    """{Datacenter name: hosts below 100 %}."""
    datacenters = read_latest_properties(suite_api_client, host_ids, [HOST_DATACENTER])
    count_by_datacenter = {}
    for host_id in host_ids:
        datacenter = datacenters.get(host_id, {}).get(HOST_DATACENTER)
        if datacenter is not None:
            count_by_datacenter.setdefault(datacenter, 0)
            count_by_datacenter[datacenter] += degraded_count([by_host[host_id]])
    return count_by_datacenter


def publish(obj, count: Optional[int]) -> None:
    """Publishes the count under vCommunity|Network."""
    if count is not None:
        obj.with_metric(f"vCommunity|{GROUP}|{COUNT_METRIC}", count)
