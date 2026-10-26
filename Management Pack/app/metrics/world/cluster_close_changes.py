#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Close for Business changes on the vSphere World object, over all clusters of all vCenters.

    Cluster Delta Close Count   the clusters whose Close for Business changed from 0 to 1
    Cluster Delta Open Count    the clusters whose Close for Business changed from 1 to 0

The change is between the Periodic Cluster Check window before and the latest window. A cluster with no Close for
Business in one of the two windows (blank, such as a new cluster) is not counted: there is no state to change from,
or to change to.

Calculated once per window, like the Periodic Cluster Check it reads, and with the same settings. It waits until
every cluster is calculated for the latest window, so a count is never taken while some clusters are still
waiting. The window is read from the stored Close for Business values, so every account publishes the same counts.
See docs/reference/metrics/vsphere-world-metrics.md.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from metrics.cluster import periodic_cluster_check as pc
from utils.ops_stats import query_resources, read_latest_timestamps, read_stat_history

logger = logging.getLogger(__name__)

CLOSE_COUNT = "Cluster Delta Close Count"
OPEN_COUNT = "Cluster Delta Open Count"
PUBLISHED_KEYS = [f"vCommunity|{CLOSE_COUNT}", f"vCommunity|{OPEN_COUNT}"]


def transition_counts(previous: Dict[str, float], current: Dict[str, float]) -> Tuple[int, int]:
    """(clusters that went from 0 to 1, clusters that went from 1 to 0), from {cluster id: Close for Business}.

    A cluster missing from either side is not counted.
    """
    closed = opened = 0
    for cluster_id, value in current.items():
        before = previous.get(cluster_id)
        if before == 0 and value == 1:
            closed += 1
        elif before == 1 and value == 0:
            opened += 1
    return closed, opened


def last_values(samples_by_cluster: Dict[str, Dict[str, List[float]]]) -> Dict[str, float]:
    """{cluster id: its last Close for Business sample}, for the clusters that have one in the window."""
    return {cluster_id: samples[pc.CLOSE_FOR_BUSINESS_KEY][-1]
            for cluster_id, samples in samples_by_cluster.items() if samples.get(pc.CLOSE_FOR_BUSINESS_KEY)}


def collect_cluster_close_changes(world_obj: Object, suite_api_client: SuiteApiClient,
                                  time_setting: Optional[str], period_setting: Optional[str],
                                  now: Optional[datetime] = None) -> None:
    """Publishes the two counts on the vSphere World object, once per window. Nothing when it is not due."""
    try:
        now = now or datetime.now(timezone.utc)
        window_end, period_hours = pc.current_window(now, time_setting, period_setting)
        end_ms = int(window_end.timestamp() * 1000)
        begin_ms = int((window_end - timedelta(hours=period_hours)).timestamp() * 1000)

        worlds = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "vSphere World", None)
        if not worlds:
            return
        world_id = worlds[0].id
        world_timestamps = read_latest_timestamps(suite_api_client, [world_id], PUBLISHED_KEYS)
        if world_timestamps is None:
            logger.warning("Cluster Delta counts: could not read when they were last published. Trying next cycle.")
            return
        # Published for this window already: their timestamp is at or after its end.
        if max(world_timestamps.get(world_id, {}).get(key, 0.0) for key in PUBLISHED_KEYS) >= end_ms:
            return

        clusters = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "ClusterComputeResource", None)
        if not clusters:
            return
        cluster_timestamps = read_latest_timestamps(
            suite_api_client, [cluster.id for cluster in clusters], pc.PUBLISHED_KEYS + pc.STAT_KEYS)
        if cluster_timestamps is None:
            logger.warning("Cluster Delta counts: could not read which clusters are calculated. Trying next cycle.")
            return
        # Wait for the Periodic Cluster Check: a cluster still due would be missing from the counts.
        still_due = sum(1 for cluster in clusters
                        if pc.is_due(cluster_timestamps.get(cluster.id, {}), begin_ms, end_ms))
        if still_due:
            logger.debug(f"Cluster Delta counts: waiting for {still_due} clusters to be calculated for the window.")
            return

        ids = [cluster.id for cluster in clusters]
        failed: List[str] = []
        previous = read_stat_history(suite_api_client, ids, [pc.CLOSE_FOR_BUSINESS_KEY], begin_ms, end_ms,
                                     pc.CLUSTERS_PER_REQUEST, failed)
        current = read_stat_history(suite_api_client, ids, [pc.CLOSE_FOR_BUSINESS_KEY], end_ms,
                                    int(now.timestamp() * 1000), pc.CLUSTERS_PER_REQUEST, failed)
        if failed:
            # Not read in full: a partial count would be wrong. Try again next cycle.
            logger.warning(f"Cluster Delta counts: {len(failed)} clusters could not be read. Trying next cycle.")
            return

        closed, opened = transition_counts(last_values(previous), last_values(current))
        world_obj.with_metric(f"vCommunity|{CLOSE_COUNT}", closed)
        world_obj.with_metric(f"vCommunity|{OPEN_COUNT}", opened)
        logger.info(f"Cluster Delta counts for the window to {pc.window_end_text(window_end)}: "
                    f"{closed} closed, {opened} opened, of {len(clusters)} clusters.")
    except Exception as e:
        # A failure here must not stop the rest of the collection.
        logger.warning(f"Failed to publish the Cluster Delta counts on vSphere World - {repr(e)}")
