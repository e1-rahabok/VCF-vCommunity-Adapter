#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Bad network packets of one ESXi host: errored and dropped packets, as a % of all its packets.

Measured in the last collection cycle (5 minutes), never as an average or a total over a longer time, so a spike is
not missed. Green (exactly 0) is "Excluded" in the source tables: bad packets are rare, so while it is 0 the row is
left out of the KPI instead of scoring a free 100. Any bad packet is yellow.

Cluster Performance uses it for the worst host of the cluster, ESXi Performance for the host itself. Each KPI names
the row its own way.
"""
from typing import Dict, List, Optional
from aria.ops.suite_api_client import SuiteApiClient
from metrics.kpi_score import Metric, has_all, percent
from utils.ops_stats import read_latest_stats

HOST_BAD_PACKET_STATS = [
    "net|errorsRx_summation_sum", "net|errorsTx_summation_sum",
    "net|droppedRx_summation_sum", "net|droppedTx_summation_sum",
]
HOST_PACKET_STATS = ["net|packetsRx_summation_sum", "net|packetsTx_summation_sum"]


def bad_network_packets_metric(name: str) -> Metric:
    """The bad network packets row, under the name the KPI gives it. The limits are the same in every KPI."""
    #             name  unit  best  green  yellow  orange  zero-at  skip-when-green
    return Metric(name, "%",  0.0,  0.0,   0.2,    0.4,    0.8,     True)


def bad_packet_pct(packets: Dict[str, float]) -> Optional[float]:
    """Errored and dropped packets of one host, as a % of all its packets, in the last collection cycle."""
    # A host with one of the six counters missing would give a wrong %.
    if not has_all(packets, HOST_BAD_PACKET_STATS + HOST_PACKET_STATS):
        return None
    bad_packets = sum(packets[key] for key in HOST_BAD_PACKET_STATS)
    all_packets = sum(packets[key] for key in HOST_PACKET_STATS)
    # None when the host sent and received no packets at all.
    return percent(bad_packets, all_packets)


def read_host_packet_stats(suite_api_client: SuiteApiClient, host_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """{host resource id: {stat key: latest value}} for the packet counters."""
    return read_latest_stats(suite_api_client, host_ids, HOST_BAD_PACKET_STATS + HOST_PACKET_STATS)
