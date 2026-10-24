#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Network Speed Degradation of one vCenter: the hosts' values and the count per Datacenter, read together.

Read once per collection cycle for the whole vCenter, because the host and Datacenter collections both publish part
of it. Called from adapter.py.
"""
import logging
from typing import Dict, NamedTuple, Optional
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from metrics.datacenter.datacenter_network_degradation import read_count_by_datacenter
from metrics.host.host_network_speed import read_host_network_speed
from utils.ops_stats import query_resources

logger = logging.getLogger(__name__)


class NetworkSpeed(NamedTuple):
    """The values of one vCenter. Empty when they could not be read."""
    by_host: Dict[str, Optional[float]]         # host resource id -> %
    count_by_datacenter: Dict[str, int]         # Datacenter name, as in summary|parentDatacenter -> hosts below 100 %


NO_DATA = NetworkSpeed({}, {})


def read_network_speed(suite_api_client: SuiteApiClient, adapter_instance_id: str) -> NetworkSpeed:
    """Reads the NIC speeds of the hosts of one vCenter, and calculates the degradation."""
    try:
        hosts = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "HostSystem", adapter_instance_id)
        host_ids = [host.id for host in hosts]
        by_host = read_host_network_speed(suite_api_client, host_ids)
        if by_host is None:
            return NO_DATA
        return NetworkSpeed(by_host, read_count_by_datacenter(suite_api_client, host_ids, by_host))
    except Exception as e:
        logger.warning(f"Failed to read the network speeds, so no Network Speed Degradation this cycle - {repr(e)}")
        return NO_DATA
