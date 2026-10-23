#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Guest OS Performance KPI.

What it is
----------
One 0-100 % score per powered-on VM. 100 is perfect. It answers one question: is the guest OS (Windows or Linux)
getting the CPU, disk and memory it needs? VM Performance scores the virtual motherboard. This KPI scores what runs
on it. All 4 rows come from VMware Tools: a VM without Tools has none of them, so it gets no Guest OS Performance KPI.

How this file is laid out
-------------------------
  Part 1  The 4 rows, one section each, in the order of the source table. Each section has the row's limits, the
          VM stat it comes from, and its formula. To add, change or remove a row, change only its section and its
          line in ROWS.
  Part 2  The KPI, once per VM: take the rows, score them and publish the KPI. The scoring is the same for every KPI:
          metrics/kpi_score.py.

The stats are read together with those of VM Performance, in one request for all VMs, by
vm_performance_metrics.read_vm_performance_stats().

Published on the VM as:
    vCommunity|Guest OS Performance|Guest OS Performance Score    the KPI
The rows are stats the VM already has, or a simple conversion of one, so they are not published again.

Called from: collectors/vm/collectVMData.py, once per powered-on VM.
Where the limits come from: docs/reference/metrics/formula/guest-os-performance.png.
Description for people who do not read code: docs/reference/metrics/guest-os-performance.md
"""
import logging
from typing import Callable, Dict, NamedTuple, Optional
from aria.ops.object import Object
from metrics.kpi_score import Metric, publish_kpi

logger = logging.getLogger(__name__)

# The names shown in VCF Operations: the group that holds the metrics, and the KPI inside it.
GROUP = "Guest OS Performance"
KPI_NAME = "Guest OS Performance"
# The key of the KPI metric. It must differ from GROUP: VCF Operations rejects a metric key that equals
# the key of its group. The metric is still shown as KPI_NAME.
KPI_KEY = "Guest OS Performance Score"

VmStats = Dict[str, float]


class Row(NamedTuple):
    """One row of the KPI: its limits, and its value from the VM's stats."""
    metric: Metric
    value: Callable[[VmStats], Optional[float]]


# =================================================================================================================
# Part 1. The 4 rows
# =================================================================================================================
#
# The five numbers of each Metric are the values where its score is 100, 75, 50, 25 and 0.
#       name                            unit    best    green   yellow  orange  zero-at

# --- Row 1. Guest CPU Run Queue per vCPU (Guest OS contention) ---------------------------------------------------
# Threads waiting for a vCPU, per vCPU. The stat is already per vCPU, so it is used as it is.
GUEST_CPU_QUEUE = "guest|20_sec_peak_cpu_queue"
CPU_QUEUE = Row(Metric("Guest CPU Run Queue per vCPU",  None,   0.0,    2.0,    4.0,    8.0,    16.0),
                lambda vm_stats: vm_stats.get(GUEST_CPU_QUEUE))

# --- Row 2. Guest Disk Queue (Guest OS contention) ---------------------------------------------------------------
# Disk IOs inside the guest OS that wait to be sent.
GUEST_DISK_QUEUE = "guest|20_sec_peak_disk_queue"
DISK_QUEUE = Row(Metric("Guest Disk Queue",             None,   0.0,    20.0,   40.0,   80.0,   160.0),
                 lambda vm_stats: vm_stats.get(GUEST_DISK_QUEUE))

# --- Row 3. Guest Free Memory (Guest OS utilization) -------------------------------------------------------------
# Free memory inside the guest OS. Higher is better, so the limits go down: 1 GB or more scores 100.
GUEST_FREE_MEMORY_KB = "guest|mem.free_latest"


def guest_free_memory_mb(vm_stats: VmStats) -> Optional[float]:
    """Free memory inside the guest OS, in MB. The stat is in KB, and the limits are in MB."""
    if GUEST_FREE_MEMORY_KB not in vm_stats:
        return None
    return vm_stats[GUEST_FREE_MEMORY_KB] / 1024.0


FREE_MEMORY = Row(Metric("Guest Free Memory",           "MB",   1024.0, 512.0,  256.0,  128.0,  0.0),
                  guest_free_memory_mb)

# --- Row 4. Guest Page-Out Rate (Guest OS utilization) -----------------------------------------------------------
# How fast the guest OS moves memory pages out to its own page file, in pages per second.
GUEST_PAGE_OUT_RATE = "guest|page.outRate_latest"
PAGE_OUT_RATE = Row(Metric("Guest Page-Out Rate",       None,   0.0,    1000.0, 2000.0, 4000.0, 8000.0),
                    lambda vm_stats: vm_stats.get(GUEST_PAGE_OUT_RATE))


# The rows, in the order of the source table.
ROWS = [CPU_QUEUE, DISK_QUEUE, FREE_MEMORY, PAGE_OUT_RATE]
METRICS = [row.metric for row in ROWS]
# Every row is a stat the VM already has, or a simple conversion of one. Only the KPI is published.
PUBLISHED_METRICS = []
# Every stat that is asked from VCF Operations, for each VM. Read by vm_performance_metrics.
VM_STATS = [GUEST_CPU_QUEUE, GUEST_DISK_QUEUE, GUEST_FREE_MEMORY_KB, GUEST_PAGE_OUT_RATE]


# =================================================================================================================
# Part 2. The KPI, once per VM
# =================================================================================================================

def guest_os_performance_values(vm_stats: VmStats) -> Dict[str, Optional[float]]:
    """The value of every row for one VM. None means "no data"."""
    return {row.metric.name: row.value(vm_stats) for row in ROWS}


def collect_guest_os_performance_metrics(vm_obj: Object, vm_name: str, vm_stats: VmStats) -> Optional[float]:
    """Publishes the Guest OS Performance KPI. Returns it, or None.

    vm_stats is the entry of this VM in the result of vm_performance_metrics.read_vm_performance_stats().
    """
    try:
        values = guest_os_performance_values(vm_stats)

        published = publish_kpi(vm_obj, GROUP, KPI_KEY, METRICS, PUBLISHED_METRICS, values)
        # Logged at debug level only: there can be thousands of VMs, and no Tools is a normal case.
        if published.no_data:
            logger.debug(f"Guest OS Performance for {vm_name}: no data, so left out: {', '.join(published.no_data)}")
        return published.score

    except Exception as e:
        # A failure here must not stop the collection of the other VM data.
        logger.warning(f"Failed to retrieve Guest OS Performance metrics for : {vm_name} - {repr(e)}")
        return None
