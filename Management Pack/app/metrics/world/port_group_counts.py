#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Number of Port Groups on the vSphere World object: the sum over all vCenters of their Number of Port Groups.

Each vCenter publishes its own count (metrics/vcenter/vcenter_port_groups.py). This metric adds up the last value of
each. It uses the configuration limit (CONFIGURATION_STALE_AFTER_MINUTES, 15 minutes), not the 10-minute limit of the
other metrics, because a port group count is based on settings and changes rarely. A vCenter whose last value is older
than that is left out, so the total falls when a vCenter stops reporting for longer than the limit.

A vCenter that has never published a count, such as one with no account of this pack, is left out.
"""
import logging
from typing import Dict
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from metrics.vcenter.vcenter_port_groups import METRIC, METRIC_KEY
from utils.ops_stats import CONFIGURATION_STALE_AFTER_MINUTES, query_resources, read_latest_stats

logger = logging.getLogger(__name__)

VCENTER_KIND = "VMwareAdapter Instance"


def total(values_by_vcenter: Dict[str, Dict[str, float]]) -> int:
    """The sum of the vCenters' counts. A vCenter without a value is not in the dict, so it is left out."""
    return int(sum(values.get(METRIC_KEY, 0.0) for values in values_by_vcenter.values() if METRIC_KEY in values))


def collect_port_group_count(world_obj: Object, suite_api_client: SuiteApiClient) -> None:
    """Publishes Number of Port Groups on the vSphere World object."""
    try:
        vcenters = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, VCENTER_KIND, None)
        values = read_latest_stats(suite_api_client, [vc.id for vc in vcenters], [METRIC_KEY],
                                   max_age_minutes=CONFIGURATION_STALE_AFTER_MINUTES)
        world_obj.with_metric(f"vCommunity|{METRIC}", total(values))
    except Exception as e:
        # A failure here must not stop the rest of the collection.
        logger.warning(f"Failed to publish {METRIC} on vSphere World - {repr(e)}")
