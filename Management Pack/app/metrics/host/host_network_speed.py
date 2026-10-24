#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Network Speed Degradation of one ESXi host (%), and the count of degraded hosts.

The speed the physical NICs run at, as a % of the speed they are configured for: sum of the actual speeds / sum of
the configured speeds x 100, over the NICs that can be compared. 100 % means no degradation. Below 100 %, a NIC
negotiated a lower speed than configured.

A NIC with no speed or speed 0 is down or unused, so it is left out. A NIC with no configured speed or 0 cannot be
compared, so it is left out. A host with no NIC left to compare has no value.

degraded_count() is the number of hosts below 100 %. The Datacenter and vSphere World counts use it.

All inputs come from VCF Operations. See docs/reference/metrics/network-speed-degradation.md, including its known limitations.
"""
import logging
from typing import Dict, List, Optional
from aria.ops.suite_api_client import SuiteApiClient
from utils.ops_stats import read_latest_instance_stats

logger = logging.getLogger(__name__)

GROUP = "Network"
HOST_METRIC = "Network Speed Degradation"

# Per physical NIC, in Mbps. VCF Operations returns one value per NIC, such as net:vmnic0|speed.
NIC_SPEED = "net|speed"
NIC_CONFIGURED_SPEED = "net|configuredSpeed"

# The host value, as stored in VCF Operations. Read for vSphere World.
STORED_HOST_VALUE = f"vCommunity|{GROUP}|{HOST_METRIC}"


def speed_degradation(speeds: Dict[str, float], configured_speeds: Dict[str, float]) -> Optional[float]:
    """Sum of actual speeds / sum of configured speeds x 100, over the NICs that can be compared.

    A NIC that is down (no speed or 0) or has no configured speed (none or 0) is left out.
    None when no NIC is left. Capped at 100 %: a NIC faster than configured is not "less degraded".
    """
    nics = [nic for nic in speeds if speeds[nic] > 0 and configured_speeds.get(nic, 0) > 0]
    if not nics:
        return None
    actual = sum(speeds[nic] for nic in nics)
    configured = sum(configured_speeds[nic] for nic in nics)
    return min(100.0, actual / configured * 100)


def degraded_count(values: List[Optional[float]]) -> int:
    """The number of hosts below 100 %. A host without a value is not counted."""
    return sum(1 for value in values if value is not None and value < 100)


def read_host_network_speed(suite_api_client: SuiteApiClient, host_ids: List[str]) -> Optional[Dict[str, Optional[float]]]:
    """{host id: %}. None when no host has any NIC speed: the request failed, so there is nothing to score."""
    nics = read_latest_instance_stats(suite_api_client, host_ids, [NIC_SPEED, NIC_CONFIGURED_SPEED])
    if host_ids and not nics:
        logger.warning("No NIC speeds for any host, so no Network Speed Degradation this cycle")
        return None
    return {
        host_id: speed_degradation(nics.get(host_id, {}).get(NIC_SPEED, {}),
                                   nics.get(host_id, {}).get(NIC_CONFIGURED_SPEED, {}))
        for host_id in host_ids
    }


def publish(obj, value: Optional[float]) -> None:
    """Publishes the host value under vCommunity|Network, rounded to two decimals."""
    if value is not None:
        obj.with_metric(f"vCommunity|{GROUP}|{HOST_METRIC}", round(value, 2))
