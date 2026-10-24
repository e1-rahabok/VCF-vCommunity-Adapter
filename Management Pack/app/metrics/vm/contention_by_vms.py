#  Copyright 2026 VCF Operations vCommunity Management Pack
"""VM contention of a group of VMs, the rows shared by Cluster Performance and ESXi Performance.

For each of 4 VM stats, two rows: how deep (the worst VM) and how broad (the 90th percentile of the VMs).
Both KPIs use these rows, so a limit changed here changes in both.
"""
from typing import Dict, List, NamedTuple, Optional
from aria.ops.suite_api_client import SuiteApiClient
from metrics.kpi_score import Metric, percentile_90
from utils.ops_stats import read_latest_stats


# =================================================================================================================
# Part 1. How deep and how broad
# =================================================================================================================

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
# Part 3. Reading the stats. One request for many VMs, never one per VM.
# =================================================================================================================

def read_vm_contention_stats(suite_api_client: SuiteApiClient, vm_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """{VM resource id: {stat key: latest value}} for the stats in VM_STATS."""
    return read_latest_stats(suite_api_client, vm_ids, list(VM_STATS))
