#  Copyright 2026 VCF Operations vCommunity Management Pack
"""VM Performance KPI.

What it is
----------
One 0-100 % score per powered-on VM. 100 is perfect. It answers one question: is the VM, as a virtual motherboard,
getting the CPU, memory, disk and network it asks for from ESXi? What happens inside the guest OS is scored
separately, by the Guest OS Performance KPI in guest_os_performance_metrics.py.

How this file is laid out
-------------------------
  Part 1  The 9 rows, one section each, in the order of the source table. Each section has the row's limits and
          where its value comes from: a VM stat as it is (8 rows), or a formula (Memory Zip Swap). To add, change or
          remove a row, change only its section and its line in ROWS.
  Part 2  Reading the stats, once per collection cycle for all VMs. The same request also reads the stats of the
          Guest OS Performance KPI.
  Part 3  The KPI, once per VM: take the rows, score them and publish. The scoring is the same for every KPI:
          metrics/kpi_score.py.

Published on the VM as:
    vCommunity|VM Performance|VM Performance Score    the KPI
    vCommunity|VM Performance|Memory Zip Swap         the one calculated row
The other rows are stats the VM already has, so publishing them again would only store every number twice, for
every VM.

Missing data: a row with no data is left out of the KPI. A powered-off VM gets no KPI at all, because its stats are
old.

Called from: collectors/vm/collectVMData.py. Stats are read once for all VMs, then the entry point runs once per
powered-on VM.
Where the limits come from: docs/reference/metrics/formula/vm-performance.png.
Description for people who do not read code: docs/reference/metrics/vm-performance.md
"""
import logging
from typing import Callable, Dict, List, NamedTuple, Optional
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from metrics.kpi_score import Metric, percent, has_all, publish_kpi
from metrics.vm import guest_os_performance_metrics
from utils.ops_stats import read_latest_stats

logger = logging.getLogger(__name__)

# The names shown in VCF Operations: the group that holds the metrics, and the KPI inside it.
GROUP = "VM Performance"
KPI_NAME = "VM Performance"
# The key of the KPI metric. It must differ from GROUP: VCF Operations rejects a metric key that equals
# the key of its group. The metric is still shown as KPI_NAME.
KPI_KEY = "VM Performance Score"

VmStats = Dict[str, float]


class Row(NamedTuple):
    """One row of the KPI: its limits, and where its value comes from: a VM stat as it is, or a formula."""
    metric: Metric
    stat: Optional[str] = None
    formula: Optional[Callable[[VmStats], Optional[float]]] = None

    def value(self, vm_stats: VmStats) -> Optional[float]:
        return vm_stats.get(self.stat) if self.stat else self.formula(vm_stats)


# =================================================================================================================
# Part 1. The 9 rows
# =================================================================================================================
#
# The five numbers of each Metric are the values where its score is 100, 75, 50, 25 and 0. A last value True means
# "skip when green": the source table marks the green range "Excluded", so the row counts in the KPI only when it is
# outside green. The CPU, memory and disk stats are the 20-second peaks, not the 5-minute averages, so the KPI is a
# leading indicator.
#       name                    unit    best    green   yellow  orange  zero-at  skip-when-green

# --- Row 1. CPU Co-Stop (VM contention) --------------------------------------------------------------------------
# Time the VM was held back so that its vCPUs stay in step. Only multi-vCPU VMs have it.
CO_STOP = Row(Metric("CPU Co-Stop",           "%",    0.0,    1.0,    2.0,    4.0,    8.0),
              stat="cpu|20_sec_peak_costopPct")

# --- Row 2. CPU Ready (VM contention) ----------------------------------------------------------------------------
# Time the VM was ready to run but had to wait for a physical CPU.
READY = Row(Metric("CPU Ready",               "%",    0.0,    2.0,    4.0,    8.0,    16.0),
            stat="cpu|20_sec_peak_readyPct")

# --- Row 3. CPU Overlap (VM contention) --------------------------------------------------------------------------
# Time the VM was interrupted so that ESXi could do work for something else.
# Green (below 0.5 %) is "Excluded": some overlap is normal and says nothing about performance.
OVERLAP = Row(Metric("CPU Overlap",           "%",    0.0,    0.5,    1.0,    2.0,    4.0,     True),
              stat="cpu|20_sec_peak_overlap")

# --- Row 4. Memory Contention (VM contention) --------------------------------------------------------------------
# Time the VM waited for memory that the host had swapped out or compressed.
MEMORY_CONTENTION = Row(Metric("Memory Contention", "%", 0.0,  0.5,    1.0,    2.0,    4.0),
                        stat="mem|20_sec_peak_host_contentionPct")

# --- Row 5. Disk Latency (VM contention) -------------------------------------------------------------------------
# Read and write latency of the VM's virtual disks.
DISK_LATENCY = Row(Metric("Disk Latency",     "ms",   0.0,    10.0,   20.0,   40.0,   80.0),
                   stat="virtualDisk|20_sec_peak_totalLatency_average")

# --- Row 6. Network Dropped Tx (VM contention) -------------------------------------------------------------------
# Packets the VM sent that were dropped, as a % of the packets it sent.
# Green (exactly 0) is "Excluded": dropped packets are rare. Any dropped packet is yellow.
DROPPED_TX = Row(Metric("Network Dropped Tx", "%",    0.0,    0.0,    0.5,    1.0,    2.0,     True),
                 stat="net|droppedTxPct_max")

# --- Row 7. CPU Run (VM utilization) -----------------------------------------------------------------------------
# Time the VM really ran on a physical CPU. Near 100 % the VM itself is too small.
# Green (below 95 %) is "Excluded": a VM that is not busy says nothing about its performance.
CPU_RUN = Row(Metric("CPU Run",               "%",    0.0,    95.0,   97.0,   99.0,   100.0,   True),
              stat="cpu|net_run")

# --- Row 8. Memory Ballooned (IaaS high utilization: the host is taking memory back from the VM) ----------------
# VM memory that the host took back through the balloon driver.
BALLOONED = Row(Metric("Memory Ballooned",    "%",    0.0,    2.0,    4.0,    8.0,    16.0),
                stat="mem|balloonPct")

# --- Row 9. Memory Zip Swap (IaaS high utilization: the host is taking memory back from the VM) -----------------
# VM memory that the host compressed or swapped out, as a % of the memory the guest OS uses. The formula is the one
# of the former "vSphere VM Memory Zip Swap" super metric, which this row replaces.
MEM_COMPRESSED = "mem|compressed_average"
MEM_SWAPPED = "mem|swapped_average"
GUEST_USED_MEMORY = "guest|used_memory"


def memory_zip_swap_pct(vm_stats: VmStats) -> Optional[float]:
    """Compressed plus swapped memory, as a % of the memory the guest OS uses.

    Divided by Guest OS Used Memory, not by VM Configured Memory, to better reflect the risk. Configured memory
    includes memory the guest OS does not use, so the % would come out smaller and under-report the problem.
    guest|used_memory comes from VMware Tools, so a VM without Tools has no Memory Zip Swap.
    """
    if not has_all(vm_stats, [MEM_COMPRESSED, MEM_SWAPPED, GUEST_USED_MEMORY]):
        return None
    return percent(vm_stats[MEM_COMPRESSED] + vm_stats[MEM_SWAPPED], vm_stats[GUEST_USED_MEMORY])


ZIP_SWAP = Row(Metric("Memory Zip Swap",      "%",    0.0,    0.25,   0.5,    1.0,    2.0),
               formula=memory_zip_swap_pct)


# The rows, in the order of the source table.
ROWS = [CO_STOP, READY, OVERLAP, MEMORY_CONTENTION, DISK_LATENCY, DROPPED_TX, CPU_RUN, BALLOONED, ZIP_SWAP]
METRICS = [row.metric for row in ROWS]
# Only the rows the VM does not already have as a stat: the calculated one.
PUBLISHED_METRICS = [row.metric for row in ROWS if row.formula]
# Row -> the VM stat it is read from, as it is.
SOURCE_STATS = {row.metric.name: row.stat for row in ROWS if row.stat}


# =================================================================================================================
# Part 2. Reading the stats, once for all VMs
# =================================================================================================================

# Every stat that is asked from VCF Operations, for each VM.
VM_STATS = list(SOURCE_STATS.values()) + [MEM_COMPRESSED, MEM_SWAPPED, GUEST_USED_MEMORY]


def read_vm_performance_stats(suite_api_client: SuiteApiClient, vm_ids: List[str]) -> Dict[str, VmStats]:
    """Returns {VM resource id: {stat key: latest value}} for all VMs, read in bulk instead of one call per VM.

    Reads the stats of both per-VM KPIs, VM Performance and Guest OS Performance, in the same request.
    """
    stat_keys = VM_STATS + [key for key in guest_os_performance_metrics.VM_STATS if key not in VM_STATS]
    try:
        return read_latest_stats(suite_api_client, vm_ids, stat_keys)
    except Exception as e:
        # Without stats there is no score, but the rest of the VM collection must still run.
        logger.warning(f"Failed to read VM Performance stats, so no VM or Guest OS Performance this cycle - {repr(e)}")
        return {}


# =================================================================================================================
# Part 3. The KPI, once per VM
# =================================================================================================================

def vm_performance_values(vm_stats: VmStats) -> Dict[str, Optional[float]]:
    """The value of every row for one VM. None means "no data"."""
    return {row.metric.name: row.value(vm_stats) for row in ROWS}


def collect_vm_performance_metrics(vm_obj: Object, vm_name: str, vm_stats: VmStats) -> Optional[float]:
    """Publishes the calculated row, then the VM Performance KPI. Returns the KPI, or None.

    vm_stats is the entry of this VM in the result of read_vm_performance_stats().
    """
    try:
        values = vm_performance_values(vm_stats)

        published = publish_kpi(vm_obj, GROUP, KPI_KEY, METRICS, PUBLISHED_METRICS, values)
        # Logged at debug level only: there can be thousands of VMs, and no Tools is a normal case.
        if published.no_data:
            logger.debug(f"VM Performance for {vm_name}: no data, so left out: {', '.join(published.no_data)}")
        return published.score

    except Exception as e:
        # A failure here must not stop the collection of the other VM data.
        logger.warning(f"Failed to retrieve VM Performance metrics for : {vm_name} - {repr(e)}")
        return None
