#  Copyright 2026 VCF Operations vCommunity Management Pack
"""The rows shared by Cluster Performance and ESXi Performance: VM contention and bad network packets.

Both KPIs ask the same two questions about a group of VMs, the VMs of a cluster or the VMs of one host:
    How deep?   The worst VM. Shows a problem that hits one VM hard.
    How broad?  The 90th percentile across the VMs. Shows a problem that many VMs have. 90 % of the VMs are at or
                below this value.
And both score the bad network packets of an ESXi host.

So the rows are defined here once, limits included, and both KPIs use the same definitions: a limit changed here
changes in both.

How this file is laid out
-------------------------
  Part 1  How deep and how broad: the two ways a VM stat becomes a row, common to every VM contention row.
  Part 2  The 4 VM contention stats, one section each. Each gives two rows: its worst VM and its 90th percentile.
  Part 3  Bad network packets of an ESXi host. Each KPI names this row its own way.
  Part 4  Reading the stats from VCF Operations, once for many objects.
"""
import math
from typing import Dict, List, NamedTuple, Optional
from aria.ops.suite_api_client import SuiteApiClient
from metrics.kpi_score import Metric, percent, has_all
from utils.ops_stats import read_latest_stats


# =================================================================================================================
# Part 1. How deep and how broad
# =================================================================================================================

def percentile_90(numbers: List[float]) -> Optional[float]:
    """The value that 90 % of the numbers are at or below. None when the list is empty.

    Nearest-rank method: sort the numbers and take the one at position 90 % of the count, rounded up.
    With 20 VMs that is the 18th lowest. With fewer than 10 VMs it is the highest, the same as the worst VM.
    """
    if not numbers:
        return None
    position = math.ceil(0.9 * len(numbers))
    return sorted(numbers)[position - 1]


class VmContentionRows(NamedTuple):
    """One VM stat and the two rows it gives: the worst VM (how deep) and the 90th percentile (how broad)."""
    stat: str
    worst: Metric
    percentile_90: Metric


# =================================================================================================================
# Part 2. The 4 VM contention stats
# =================================================================================================================
#
# Every row is "lower is better", and 0 is perfect. The five numbers of each Metric are the values where its score is
# 100, 75, 50, 25 and 0. The worst-VM limits are higher than the 90th-percentile limits, because a single VM peaks
# far above most of the others. The stats are the 20-second peaks, not the 5-minute averages, so the KPIs are
# leading indicators.
#       name                                 unit   best  green  yellow  orange  zero-at

# --- CPU Ready: time the VM was ready to run, but had to wait for a physical CPU ---------------------------------
CPU_READY = VmContentionRows(
    "cpu|20_sec_peak_readyPct",
    Metric("Worst VM CPU Ready",                "%",   0.0,  4.0,   8.0,    16.0,   32.0),
    Metric("90th Percentile VM CPU Ready",      "%",   0.0,  1.0,   2.0,    4.0,    8.0),
)

# --- CPU Co-Stop: time a multi-vCPU VM was held back, so that its vCPUs stay in step ------------------------------
CPU_CO_STOP = VmContentionRows(
    "cpu|20_sec_peak_costopPct",
    Metric("Worst VM CPU Co-Stop",              "%",   0.0,  2.0,   4.0,    8.0,    16.0),
    Metric("90th Percentile VM CPU Co-Stop",    "%",   0.0,  0.5,   1.0,    2.0,    4.0),
)

# --- Memory Latency: time the VM waited for memory that the host had swapped out or compressed -------------------
MEMORY_LATENCY = VmContentionRows(
    "mem|20_sec_peak_host_contentionPct",
    Metric("Worst VM Memory Latency",           "%",   0.0,  1.0,   2.0,    4.0,    8.0),
    Metric("90th Percentile VM Memory Latency", "%",   0.0,  0.5,   1.0,    2.0,    4.0),
)

# --- Disk Latency: read and write latency of the VM's virtual disks ---------------------------------------------
DISK_LATENCY = VmContentionRows(
    "virtualDisk|20_sec_peak_totalLatency_average",
    Metric("Worst VM Disk Latency",             "ms",  0.0,  40.0,  80.0,   160.0,  320.0),
    Metric("90th Percentile VM Disk Latency",   "ms",  0.0,  20.0,  40.0,   60.0,   80.0),
)

VM_CONTENTION = [CPU_READY, CPU_CO_STOP, MEMORY_LATENCY, DISK_LATENCY]

# The 8 rows, in the order of the source tables: the 4 worst-VM rows, then the 4 90th-percentile rows.
VM_CONTENTION_METRICS = [rows.worst for rows in VM_CONTENTION] + [rows.percentile_90 for rows in VM_CONTENTION]

# VM stat -> (its worst-VM row, its 90th-percentile row). The stats asked from VCF Operations for each VM.
VM_STATS = {rows.stat: (rows.worst.name, rows.percentile_90.name) for rows in VM_CONTENTION}


def worst_and_percentile(stats_by_vm: Dict[str, Dict[str, float]], vm_ids: List[str]) -> Dict[str, Optional[float]]:
    """The value of the 8 VM contention rows, over the VMs in vm_ids. None means "no data"."""
    values = {}
    for rows in VM_CONTENTION:
        # A VM that does not have this stat is left out.
        per_vm = [stats_by_vm[vm_id][rows.stat] for vm_id in vm_ids if rows.stat in stats_by_vm.get(vm_id, {})]
        values[rows.worst.name] = max(per_vm) if per_vm else None
        values[rows.percentile_90.name] = percentile_90(per_vm)
    return values


# =================================================================================================================
# Part 3. Bad network packets of an ESXi host
# =================================================================================================================
#
# Errored and dropped packets, as a % of all packets, in the last collection cycle (5 minutes). Never an average or a
# total over a longer time, so a spike is not missed. Green (exactly 0) is "Excluded" in the source tables: bad
# packets are rare, so while it is 0 the row is left out of the KPI instead of scoring a free 100. Any bad packet is
# yellow.

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


# =================================================================================================================
# Part 4. Reading the stats. One request for many objects, never one per object.
# =================================================================================================================

def read_vm_contention_stats(suite_api_client: SuiteApiClient, vm_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """{VM resource id: {stat key: latest value}} for the stats in VM_STATS."""
    return read_latest_stats(suite_api_client, vm_ids, list(VM_STATS))


def read_host_packet_stats(suite_api_client: SuiteApiClient, host_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """{host resource id: {stat key: latest value}} for the packet counters."""
    return read_latest_stats(suite_api_client, host_ids, HOST_BAD_PACKET_STATS + HOST_PACKET_STATS)
