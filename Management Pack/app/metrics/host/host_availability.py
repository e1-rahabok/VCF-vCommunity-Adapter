#  Copyright 2026 VCF Operations vCommunity Management Pack
"""ESXi Host Operational Availability (%, per host).

25 points for each condition met: powered on, connected, not in maintenance, not in quarantine. So a host is 0, 25,
50, 75 or 100 %. Hardware redundancy is not part of it: workloads can run fine on a host that has lost a redundant
component.

A host with no data counts as 0 %, not left out: leaving it out would make its cluster look better. When no host has
any data at all, the request to VCF Operations failed, so nothing is published.

All inputs come from VCF Operations. See docs/reference/metrics/operational-availability.md, including its known limitations.
"""
import logging
from typing import Dict, List, Optional
from aria.ops.suite_api_client import SuiteApiClient
from utils.ops_inventory import HostInfo
from utils.ops_stats import read_latest_properties, read_latest_stats

logger = logging.getLogger(__name__)

GROUP = "Availability"
HOST_METRIC = "ESXi Host Operational Availability"

# The three properties are compared with these exact values.
HOST_POWERED_ON = "sys|poweredOn"                       # stat: 1 when powered on
HOST_CONDITIONS = {
    "runtime|connectionState": "connected",
    "runtime|maintenanceState": "notInMaintenance",
    "runtime|quarantineState": "notInQuarantine",
}
POINTS_PER_CONDITION = 25.0


def host_availability(powered_on: Optional[float], properties: Dict[str, str]) -> float:
    """0, 25, 50, 75 or 100. A condition with no data is not met."""
    conditions_met = [powered_on == 1]
    conditions_met += [properties.get(key) == value for key, value in HOST_CONDITIONS.items()]
    return POINTS_PER_CONDITION * sum(conditions_met)


def read_host_availability(suite_api_client: SuiteApiClient, hosts: List[HostInfo]) -> Optional[Dict[str, float]]:
    """{host id: %}. None when no host has any data: the requests failed, so there is nothing to score."""
    host_ids = [host.id for host in hosts]
    stats = read_latest_stats(suite_api_client, host_ids, [HOST_POWERED_ON])
    properties = read_latest_properties(suite_api_client, host_ids, list(HOST_CONDITIONS))
    if host_ids and not stats and not properties:
        logger.warning("No Operational Availability data for any host, so none is published this cycle")
        return None
    return {
        host_id: host_availability(stats.get(host_id, {}).get(HOST_POWERED_ON), properties.get(host_id, {}))
        for host_id in host_ids
    }


def publish(obj, value: Optional[float]) -> None:
    """Publishes the host value under vCommunity|Availability, rounded to two decimals."""
    if value is not None:
        obj.with_metric(f"vCommunity|{GROUP}|{HOST_METRIC}", round(value, 2))
