#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Total Network Speed Degradation on vSphere World: the number of hosts below 100 %, over all hosts of all vCenters.

Read from the stored host values, so it has the known limitations of the other vSphere World metrics.
"""
import logging
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from metrics.datacenter.datacenter_network_degradation import COUNT_METRIC
from metrics.host.host_network_speed import GROUP, STORED_HOST_VALUE, degraded_count
from utils.ops_stats import query_resources, read_latest_stats

logger = logging.getLogger(__name__)


def collect_world_network_speed(world_obj: Object, suite_api_client: SuiteApiClient) -> None:
    """Publishes Total Network Speed Degradation on vSphere World, from the stored values of all hosts."""
    try:
        hosts = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "HostSystem", None)
        stats = read_latest_stats(suite_api_client, [host.id for host in hosts], [STORED_HOST_VALUE])
        if not stats:
            return      # nothing stored yet, or the request failed: no count rather than a false 0
        values = [host_stats.get(STORED_HOST_VALUE) for host_stats in stats.values()]
        world_obj.with_metric(f"vCommunity|{GROUP}|{COUNT_METRIC}", degraded_count(values))
    except Exception as e:
        logger.warning(f"Failed to publish Total Network Speed Degradation on vSphere World - {repr(e)}")
