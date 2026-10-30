#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com
"""DRS Score: vCenter's own 0-100 score for a cluster, published as it is read. Not a KPI.

Read from the "summary" property of the cluster in vCenter (summary.drsScore). Published as 0 when DRS is disabled
or when vCenter reports a negative score.

Published on the cluster as vCommunity|Cluster Configuration|Distributed Resource Scheduler|DRS Score.
Called from: collectors/cluster/collectClusterData.py, once per cluster.
"""

import logging

logger = logging.getLogger(__name__)


def collect_drs_metrics(cluster_obj, cluster_name, prop_dict):
    """Publishes the DRS Score of one cluster. prop_dict holds the cluster properties read from vCenter."""
    try:
        drsScore = "vCommunity|Cluster Configuration|Distributed Resource Scheduler|DRS Score"
        drsSummary = prop_dict.get("summary")
        drsScoreValue= drsSummary.drsScore
        drsEnabled = prop_dict.get("configuration.drsConfig.enabled")

        # DRS is off, so vCenter has no meaningful score for this cluster
        if not drsEnabled:
            cluster_obj.with_metric(drsScore, 0)

        # A negative score is not a real score
        elif drsScoreValue < 0:
            cluster_obj.with_metric(drsScore, 0)

        # The normal case: publish the score as a whole number
        else:
            cluster_obj.with_metric(drsScore, int(drsScoreValue))

        logger.debug(f"Successfully collected vSphere Cluster DRS metrics for the cluster: {cluster_name}")

    except Exception as e:
        # A failure here must not stop the collection of the other cluster data
        logger.warning(f"Failed to retrieve vSphere Cluster DRS metrics for : {cluster_name} - {repr(e)}")
