#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Performance KPI: one 0-100 % score per vSphere cluster, 100 is perfect.

It measures actual contention of the cluster's VMs, not potential: are the VMs in this cluster getting the CPU,
memory, disk and network they ask for?

Published on the cluster as vCommunity|Cluster Performance|Cluster Performance Score (the KPI) and its 9 rows.
A row with no data is left out of the KPI, never treated as 0.

Called from: collectors/cluster/collectClusterData.py, once per cluster.
Limits: docs/reference/metrics/formula/cluster-performance.png. Description: docs/reference/metrics/cluster-performance.md
"""
import logging
from typing import Dict, List, Optional
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from metrics.kpi_score import publish_kpi
from metrics.host.host_bad_network_packets import bad_network_packets_metric, bad_packet_pct, read_host_packet_stats
from metrics.vm.contention_by_vms import VM_CONTENTION_METRICS, worst_and_percentile, read_vm_contention_stats

logger = logging.getLogger(__name__)

# The names shown in VCF Operations: the group that holds the metrics, and the KPI inside it.
GROUP = "Cluster Performance"
KPI_NAME = "Cluster Performance"
# The key of the KPI metric. It must differ from GROUP: VCF Operations rejects a metric key that equals
# the key of its group. The metric is still shown as KPI_NAME.
KPI_KEY = "Cluster Performance Score"


# =================================================================================================================
# Part 1. The 9 rows
# =================================================================================================================

# --- Rows 1-8. VM contention: how deep (the worst VM) and how broad (the 90th percentile) -----------------------
# Defined in metrics/vm/contention_by_vms.py, shared with ESXi Performance.

# --- Row 9. Bad network packets: the ESXi host of the cluster where they are highest -------------------------------
BAD_PACKETS = bad_network_packets_metric("Highest ESXi Bad Network Packets")


def highest_host_bad_packet_pct(suite_api_client: SuiteApiClient, host_ids: List[str]) -> Optional[float]:
    """The highest % of errored or dropped packets of any one host, in the last collection cycle (5 minutes)."""
    packets_by_host = read_host_packet_stats(suite_api_client, host_ids)
    per_host = [bad_packet_pct(packets) for packets in packets_by_host.values()]
    per_host = [pct for pct in per_host if pct is not None]
    return max(per_host) if per_host else None


# The rows, in the order of the source table. Every row is published on the cluster: none exists there already.
METRICS = VM_CONTENTION_METRICS + [BAD_PACKETS]
PUBLISHED_METRICS = METRICS


# =================================================================================================================
# Part 2. The KPI
# =================================================================================================================

def vm_contention_values(suite_api_client: SuiteApiClient, vm_ids: List[str]) -> Dict[str, Optional[float]]:
    """Rows 1-8, over the cluster's powered-on VMs, read in one request."""
    return worst_and_percentile(read_vm_contention_stats(suite_api_client, vm_ids), vm_ids)


def collect_cluster_performance_metrics(
    cluster_obj: Object,
    cluster_name: str,
    vm_ids: List[str],
    host_ids: List[str],
    suite_api_client: SuiteApiClient
) -> None:
    """Publishes the rows, then the Cluster Performance KPI computed from them.

    vm_ids are the VCF Operations ids of the cluster's powered-on VMs, host_ids those of its ESXi hosts.
    """
    try:
        values = vm_contention_values(suite_api_client, vm_ids)
        values[BAD_PACKETS.name] = highest_host_bad_packet_pct(suite_api_client, host_ids)

        no_data = publish_kpi(cluster_obj, GROUP, KPI_KEY, METRICS, PUBLISHED_METRICS, values).no_data
        if no_data:
            logger.info(f"Cluster Performance for {cluster_name}: no data, so left out: {', '.join(no_data)}")

    except Exception as e:
        # A failure here must not stop the collection of the other cluster data.
        logger.warning(f"Failed to retrieve vSphere Cluster Performance metrics for : {cluster_name} - {repr(e)}")
