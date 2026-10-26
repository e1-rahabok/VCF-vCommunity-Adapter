#  Copyright 2026 VCF Operations vCommunity Management Pack

import logging
from typing import List, Optional
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from metrics.world.cluster_summary_metrics import collect_cluster_summary_metrics
from metrics.world.availability_summary_metrics import collect_availability_summary_metrics
from metrics.world.cluster_close_changes import collect_cluster_close_changes
from metrics.world.vsphere_network_degradation import collect_world_network_speed

logger = logging.getLogger(__name__)


def collect_world_data(suite_api_client: SuiteApiClient, result: CollectResult,
                       check_time: Optional[str] = None, check_period: Optional[str] = None) -> None:
    """Publishes the summary metrics on the vSphere World object. There is one, for all vCenters.

    check_time and check_period are the Periodic Cluster Check settings, for the Cluster Delta counts.
    """
    try:
        worlds: List[Object] = suite_api_client.query_for_resources(
            {"adapterKind": [VCENTER_ADAPTER_KIND], "resourceKind": ["vSphere World"]}
        )
        if not worlds:
            logger.debug("No vSphere World object found in VCF Operations. Skipping the summary metrics.")
            return

        world_obj = worlds[0]
        collect_cluster_summary_metrics(world_obj, suite_api_client)
        collect_availability_summary_metrics(world_obj, suite_api_client)
        collect_world_network_speed(world_obj, suite_api_client)
        collect_cluster_close_changes(world_obj, suite_api_client, check_time, check_period)
        result.add_object(world_obj)

    except Exception as e:
        logger.warning(f"Failed to collect vSphere World data - {repr(e)}")
