#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Operational Availability of one vCenter: its hosts and clusters, read together, and the worst cluster.

Worst Cluster Operational Availability (%, per vCenter): the lowest Cluster Operational Availability of the clusters
of this account's vCenter.

Read once per collection cycle for the whole vCenter, because the host, cluster and vCenter collections all publish
part of it. Called from adapter.py.

All inputs come from VCF Operations. See docs/reference/metrics/operational-availability.md, including its known limitations.
"""
import logging
from typing import Dict, List, NamedTuple, Optional
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from metrics.cluster.cluster_availability import read_cluster_availability
from metrics.host.host_availability import GROUP, read_host_availability
from utils.ops_inventory import read_hosts
from utils.ops_stats import query_resources

logger = logging.getLogger(__name__)

WORST_CLUSTER_METRIC = "Worst Cluster Operational Availability"


class OperationalAvailability(NamedTuple):
    """The values of one vCenter. Empty when they could not be read."""
    by_host: Dict[str, float]                   # host resource id -> %
    by_cluster: Dict[str, Optional[float]]      # cluster name, as in summary|parentCluster -> %

    def worst_cluster(self) -> Optional[float]:
        return worst(list(self.by_cluster.values()))


NO_DATA = OperationalAvailability({}, {})


def worst(values: List[Optional[float]]) -> Optional[float]:
    """The lowest value. A cluster without a value is left out. None when there is none."""
    known = [value for value in values if value is not None]
    return min(known) if known else None


def read_operational_availability(suite_api_client: SuiteApiClient, adapter_instance_id: str) -> OperationalAvailability:
    """Reads the hosts and clusters of one vCenter, and calculates their Operational Availability."""
    try:
        hosts = read_hosts(suite_api_client, adapter_instance_id)
        by_host = read_host_availability(suite_api_client, hosts)
        if by_host is None:
            return NO_DATA
        clusters = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "ClusterComputeResource", adapter_instance_id)
        by_cluster = read_cluster_availability(suite_api_client, clusters, hosts, by_host)
        return OperationalAvailability(by_host, by_cluster)
    except Exception as e:
        logger.warning(f"Failed to read Operational Availability, so none this cycle - {repr(e)}")
        return NO_DATA


def publish(obj, value: Optional[float]) -> None:
    """Publishes the worst cluster value under vCommunity|Availability, rounded to two decimals."""
    if value is not None:
        obj.with_metric(f"vCommunity|{GROUP}|{WORST_CLUSTER_METRIC}", round(value, 2))
