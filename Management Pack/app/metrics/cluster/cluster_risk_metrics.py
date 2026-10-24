#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Risk KPI.

What it is
----------
One 0-100 % score per vSphere cluster. 0 is no risk, 100 is maximum risk: higher is worse, as the name says. It is a
leading indicator: it warns before the VMs feel contention, and covers both capacity and performance. Cluster
Performance shows contention that is happening now. Cluster Risk shows how close the cluster is to it.

Every row takes the highest or worst ESXi host, not the cluster average, because one full host can hurt its VMs
while the cluster average still looks fine.

How this file is laid out
-------------------------
  Part 1  What several rows use, defined once: the host and its VMs, the host's DRAM capacity, and the size at which
          a VM becomes a monster.
  Part 2  The 12 rows, one section each, in the order of the source table. Each section has the row's limits, the
          host stats it reads, and its formula for one host. To add, change or remove a row, change only its
          section and its line in ROWS.
  Part 3  The KPI: read the stats of the cluster's hosts, calculate each row per host, keep the highest host,
          score and publish. The scoring is the same for every KPI (metrics/kpi_score.py). The published Cluster
          Risk is 100 minus the weighted average of the row scores (HIGHER_IS_WORSE).

Published on the cluster as:
    vCommunity|Cluster Risk|Cluster Risk Score    the KPI
    vCommunity|Cluster Risk|<row name>            each of the 12 rows

Missing data: a row with no data is not published and is left out of the KPI. It is never treated as 0, because 0
means "no risk". A host without NVMe memory tiering has no Memory Tiering Latency, so that row is left out for it.

Called from: collectors/cluster/collectClusterData.py, once per cluster.
Where the limits come from: docs/reference/metrics/formula/cluster-risk.png. Six green ranges are "Excluded": while
green, those rows are left out of the KPI rather than scored 100, see "Skip when green" in metrics/kpi_score.py.
Description for people who do not read code: docs/reference/metrics/cluster-risk.md
"""
import logging
from typing import Callable, Dict, List, NamedTuple, Optional
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from metrics.kpi_score import Metric, percent, has_all, publish_kpi
from utils.ops_stats import read_latest_stats
from utils.ops_inventory import VmInfo

logger = logging.getLogger(__name__)

# The names shown in VCF Operations: the group that holds the metrics, and the KPI inside it.
GROUP = "Cluster Risk"
KPI_NAME = "Cluster Risk"
# The key of the KPI metric. It must differ from GROUP: VCF Operations rejects a metric key that equals
# the key of its group. The metric is still shown as KPI_NAME.
KPI_KEY = "Cluster Risk Score"
# Published as 100 minus the score: 100 = maximum risk. See publish_kpi() in metrics/kpi_score.py.
HIGHER_IS_WORSE = True

HostStats = Dict[str, float]


# =================================================================================================================
# Part 1. What several rows use
# =================================================================================================================

# --- The host and its VMs ----------------------------------------------------------------------------------------
class HostInventory(NamedTuple):
    """What the collector knows about one host of the cluster. See utils/ops_inventory.py."""
    host_id: str                    # VCF Operations resource id, for the stats API
    cores: Optional[float]          # physical cores
    threads: Optional[float]        # CPU threads
    vms: List[VmInfo]               # its powered-on VMs


# --- The host's DRAM capacity ------------------------------------------------------------------------------------
# In KB: DRAM (the DIMMs) only, never DRAM plus a memory tier such as NVMe. Every memory row of this KPI is measured
# against it: there is no use case, in Risk or Performance, for comparing against DRAM plus NVMe.
MEM_DRAM_CAPACITY = "mem:DRAM|memory_tier_total_capacity"
# Used when MEM_DRAM_CAPACITY returns nothing.
MEM_DRAM_CAPACITY_FALLBACK = "mem|host_provisioned"                     # KB
DRAM_STATS = [MEM_DRAM_CAPACITY, MEM_DRAM_CAPACITY_FALLBACK]


def dram_capacity_kb(stats: HostStats) -> Optional[float]:
    """The host's DRAM, in KB. Falls back to MEM_DRAM_CAPACITY_FALLBACK when the DRAM stat has nothing."""
    return stats.get(MEM_DRAM_CAPACITY) or stats.get(MEM_DRAM_CAPACITY_FALLBACK) or None


def percent_of_dram(stats: HostStats, memory_kb: float) -> Optional[float]:
    """memory_kb as a % of the host's DRAM."""
    dram_kb = dram_capacity_kb(stats)
    if dram_kb is None:
        return None
    return percent(memory_kb, dram_kb)


# --- The size at which a VM becomes a monster on its host --------------------------------------------------------
# Three account settings (Advanced Settings), with these defaults:
# CPU: more than 50 % of the host's physical cores. Cores, not threads: on a host with 64 cores and 128 threads, a VM
# with more than 32 vCPUs is a monster.
# Memory: more than 40 % of the host's DRAM, or 256 GB, whichever is smaller. A memory tier such as NVMe does not
# count. On a host with 768 GB of DRAM and 768 GB of NVMe, a VM of 256 GB is a monster.
MONSTER_CPU_SETTING = "monster_vm_cpu_percent_of_cores"
MONSTER_MEMORY_SETTING = "monster_vm_memory_percent_of_dram"
MONSTER_MEMORY_MIN_SETTING = "monster_vm_memory_min_gb"
DEFAULT_MONSTER_CPU_PERCENT = 50
DEFAULT_MONSTER_MEMORY_PERCENT = 40
DEFAULT_MONSTER_MEMORY_MIN_GB = 256


class MonsterVmSize(NamedTuple):
    """The size at which a VM becomes a monster on its host. See the settings above."""
    ratio_of_cores: float           # 0.5 = 50 % of the host's physical cores
    ratio_of_dram: float            # 0.4 = 40 % of the host's DRAM ...
    memory_min_mb: float            # ... or this, whichever is smaller: a VM this big is a monster on any host


def parse_setting(text, default: int, label: str, highest: Optional[int] = None) -> int:
    """A whole number from 1 to highest. An empty or invalid setting falls back to default, with a warning."""
    value = str(text if text is not None else "").strip()
    if value.isdigit() and 1 <= int(value) and (highest is None or int(value) <= highest):
        return int(value)
    if value:
        allowed = f"from 1 to {highest}" if highest else "of 1 or more"
        logger.warning(f"{label} '{text}' is not a whole number {allowed}. Using {default}.")
    return default


def monster_vm_size(cpu_percent=None, memory_percent=None, memory_min_gb=None) -> MonsterVmSize:
    """The Monster VM size from the three account settings, as get_identifier_value returns them."""
    return MonsterVmSize(
        parse_setting(cpu_percent, DEFAULT_MONSTER_CPU_PERCENT, "Monster VM CPU (% of host cores)", 100) / 100.0,
        parse_setting(memory_percent, DEFAULT_MONSTER_MEMORY_PERCENT, "Monster VM Memory (% of host DRAM)", 100) / 100.0,
        parse_setting(memory_min_gb, DEFAULT_MONSTER_MEMORY_MIN_GB, "Monster VM Memory Minimum (GB)") * 1024.0,
    )


DEFAULT_MONSTER_VM = monster_vm_size()


class RiskRow(NamedTuple):
    """One row of the KPI: its limits, the host stats it reads, and its value for one host."""
    metric: Metric
    stats: List[str]
    value: Callable[[HostStats, HostInventory, MonsterVmSize], Optional[float]]


# =================================================================================================================
# Part 2. The 12 rows
# =================================================================================================================
#
# Every row is "lower is better". The five numbers of each Metric are the values where its score is 100, 75, 50, 25
# and 0. A last value True means "skip when green": the source table marks the green range "Excluded", so the row
# counts in the KPI only when it is outside green. Memory stats are in KB, CPU capacity in MHz.
#       name                                      unit   best  green  yellow  orange  zero-at  skip-when-green

# ----- Utilization: how busy the busiest host is -----------------------------------------------------------------

# --- Row 1. Highest ESXi CPU Thread Utilization ------------------------------------------------------------------
# The % of the host's CPU threads in use (cpu.utilization). Green (below 60 %) is "Excluded": a host that is not
# busy says nothing about risk.
CPU_THREAD_UTIL = "cpu|utilization_average"


def cpu_thread_utilization_pct(stats: HostStats) -> Optional[float]:
    return stats.get(CPU_THREAD_UTIL)


THREAD_UTILIZATION = RiskRow(
    Metric("Highest ESXi CPU Thread Utilization",     "%",   0.0,  60.0,  80.0,   90.0,   95.0,   True),
    [CPU_THREAD_UTIL], lambda stats, host, monster: cpu_thread_utilization_pct(stats))

# --- Row 2. Worst ESXi CPU Imbalance -----------------------------------------------------------------------------
# Running CPU threads divided by running CPU cores. 1 means one thread runs on each busy core; 2 means both
# hyper-threads run on every busy core. Green is exactly 1, as in the source table: any imbalance is yellow.
CPU_CORE_UTIL = "cpu|coreUtilization_average"           # cpu.coreUtilization: % of the host's CPU cores in use


def cpu_imbalance(stats: HostStats, host: HostInventory) -> Optional[float]:
    """Count of running CPU threads / count of running CPU cores, on one host."""
    if not host.cores or not host.threads or not has_all(stats, [CPU_THREAD_UTIL, CPU_CORE_UTIL]):
        return None
    running_threads = stats[CPU_THREAD_UTIL] / 100.0 * host.threads
    running_cores = stats[CPU_CORE_UTIL] / 100.0 * host.cores
    # None when no core is running: an idle host has no imbalance to speak of.
    if running_cores <= 0:
        return None
    return running_threads / running_cores


IMBALANCE = RiskRow(
    Metric("Worst ESXi CPU Imbalance",                None,  1.0,  1.0,   1.3,    1.6,    2.0),
    [CPU_THREAD_UTIL, CPU_CORE_UTIL], lambda stats, host, monster: cpu_imbalance(stats, host))

# --- Row 3. Highest ESXi Memory Consumed -------------------------------------------------------------------------
# Consumed memory, as a % of the host's DRAM. Green (below 80 %) is "Excluded": a host that is not full says nothing
# about risk.
MEM_CONSUMED = "mem|consumed_average"


def memory_consumed_pct(stats: HostStats) -> Optional[float]:
    if MEM_CONSUMED not in stats:
        return None
    return percent_of_dram(stats, stats[MEM_CONSUMED])


MEMORY_CONSUMED = RiskRow(
    Metric("Highest ESXi Memory Consumed",            "%",   0.0,  80.0,  90.0,   95.0,   100.0,  True),
    [MEM_CONSUMED], lambda stats, host, monster: memory_consumed_pct(stats))

# ----- Saturation: the host is already reclaiming memory from its VMs ---------------------------------------------

# --- Row 4. Worst ESXi Memory Ballooned --------------------------------------------------------------------------
# Ballooned memory, as a % of the host's DRAM.
MEM_BALLOONED = "mem|vmmemctl_average"


def memory_ballooned_pct(stats: HostStats) -> Optional[float]:
    if MEM_BALLOONED not in stats:
        return None
    return percent_of_dram(stats, stats[MEM_BALLOONED])


BALLOONED = RiskRow(
    Metric("Worst ESXi Memory Ballooned",             "%",   0.0,  1.0,   2.0,    4.0,    8.0),
    [MEM_BALLOONED], lambda stats, host, monster: memory_ballooned_pct(stats))

# --- Row 5. Worst ESXi Memory Zip Swap ---------------------------------------------------------------------------
# Compressed (zipped) plus swapped memory, as a % of the host's DRAM. The same stats as the former "Memory Zip Swap"
# super metric.
MEM_COMPRESSED = "mem|compressed_average"
MEM_SWAPPED = "mem|swapout_average"


def memory_zip_swap_pct(stats: HostStats) -> Optional[float]:
    """Compressed plus swapped memory of the host, added up, as a % of its DRAM."""
    if not has_all(stats, [MEM_COMPRESSED, MEM_SWAPPED]):
        return None
    return percent_of_dram(stats, stats[MEM_COMPRESSED] + stats[MEM_SWAPPED])


ZIP_SWAP = RiskRow(
    Metric("Worst ESXi Memory Zip Swap",              "%",   0.0,  0.25,  0.5,    1.0,    2.0),
    [MEM_COMPRESSED, MEM_SWAPPED], lambda stats, host, monster: memory_zip_swap_pct(stats))

# --- Row 6. Worst ESXi Memory Tiering Latency --------------------------------------------------------------------
# Read latency of the NVMe memory tier, in µs (confirmed). Only hosts with memory tiering have it.
MEM_TIERING_LATENCY = "mem:NVMe|latency.read_latest"


def memory_tiering_latency(stats: HostStats) -> Optional[float]:
    """Read latency of the NVMe memory tier. None on a host without memory tiering."""
    return stats.get(MEM_TIERING_LATENCY)


TIERING_LATENCY = RiskRow(
    Metric("Worst ESXi Memory Tiering Latency",       "µs",  0.0,  150.0, 300.0,  450.0,  600.0),
    [MEM_TIERING_LATENCY], lambda stats, host, monster: memory_tiering_latency(stats))

# ----- Reservation: capacity promised to VMs, even when they do not use it ----------------------------------------

# --- Row 7. Highest ESXi CPU Reservation -------------------------------------------------------------------------
# CPU reserved for VMs, as a % of the host's CPU capacity, both in MHz. Green (below 10 %) is "Excluded": little
# reservation says nothing about risk.
CPU_RESERVED = "cpu|reservedCapacity_average"           # MHz reserved for VMs
CPU_CAPACITY = "cpu|totalCapacity_average"              # MHz


def cpu_reservation_pct(stats: HostStats) -> Optional[float]:
    """CPU reserved for VMs, as a % of the host's CPU capacity."""
    if not has_all(stats, [CPU_RESERVED, CPU_CAPACITY]):
        return None
    return percent(stats[CPU_RESERVED], stats[CPU_CAPACITY])


CPU_RESERVATION = RiskRow(
    Metric("Highest ESXi CPU Reservation",            "%",   0.0,  10.0,  40.0,   60.0,   80.0,   True),
    [CPU_RESERVED, CPU_CAPACITY], lambda stats, host, monster: cpu_reservation_pct(stats))

# --- Row 8. Highest ESXi Memory Reservation ----------------------------------------------------------------------
# Memory reserved for VMs, as a % of the host's DRAM. Green (below 10 %) is "Excluded".
MEM_RESERVED = "mem|reservedCapacity_average"


def memory_reservation_pct(stats: HostStats) -> Optional[float]:
    """Memory reserved for VMs, as a % of the host's DRAM."""
    if MEM_RESERVED not in stats:
        return None
    return percent_of_dram(stats, stats[MEM_RESERVED])


MEMORY_RESERVATION = RiskRow(
    Metric("Highest ESXi Memory Reservation",         "%",   0.0,  10.0,  40.0,   60.0,   80.0,   True),
    [MEM_RESERVED], lambda stats, host, monster: memory_reservation_pct(stats))

# ----- Allocation: vCPU and memory allocated to the powered-on VMs, against what the host has ---------------------

# --- Row 9. Highest ESXi CPU Overcommit Ratio --------------------------------------------------------------------
# vCPUs allocated to the powered-on VMs, per physical core. Green (below 1, no overcommit) is "Excluded".
# VCF Operations adds up the VMs, so the code does not have to.
VCPUS_ALLOCATED = "cpu|vcpus_allocated_on_all_powered_on_vms"            # number of vCPUs


def cpu_overcommit(stats: HostStats, host: HostInventory) -> Optional[float]:
    """vCPUs allocated to the powered-on VMs, per physical core of the host."""
    if not host.cores or VCPUS_ALLOCATED not in stats:
        return None
    return stats[VCPUS_ALLOCATED] / host.cores


CPU_OVERCOMMIT = RiskRow(
    Metric("Highest ESXi CPU Overcommit Ratio",       None,  0.0,  1.0,   2.0,    3.0,    4.0,    True),
    [VCPUS_ALLOCATED], lambda stats, host, monster: cpu_overcommit(stats, host))

# --- Row 10. Highest ESXi Memory Overcommit Ratio ----------------------------------------------------------------
# Memory allocated to the powered-on VMs, per KB of the host's DRAM. Both are in KB. Green (below 1) is "Excluded".
MEM_ALLOCATED = "mem|memory_allocated_on_all_powered_on_vms"             # KB


def memory_overcommit(stats: HostStats) -> Optional[float]:
    """Memory allocated to the powered-on VMs, per KB of the host's DRAM."""
    dram_kb = dram_capacity_kb(stats)
    if MEM_ALLOCATED not in stats or dram_kb is None:
        return None
    return stats[MEM_ALLOCATED] / dram_kb


MEMORY_OVERCOMMIT = RiskRow(
    Metric("Highest ESXi Memory Overcommit Ratio",    None,  0.0,  1.0,   1.4,    1.8,    2.2,    True),
    [MEM_ALLOCATED], lambda stats, host, monster: memory_overcommit(stats))

# ----- Monster VM: the largest VM against the size where a VM becomes a monster on its host (Part 1) ---------------
# 1 means the largest VM is exactly at that size.

# --- Row 11. Highest CPU Monster VM to Host Ratio ----------------------------------------------------------------
def cpu_monster_ratio(host: HostInventory, monster: MonsterVmSize = DEFAULT_MONSTER_VM) -> Optional[float]:
    """vCPUs of the largest VM, against the vCPUs at which a VM becomes a monster on this host."""
    vcpus = [vm.vcpus for vm in host.vms if vm.vcpus]
    if not host.cores or not vcpus:
        return None
    return max(vcpus) / (monster.ratio_of_cores * host.cores)


CPU_MONSTER = RiskRow(
    Metric("Highest CPU Monster VM to Host Ratio",    None,  0.0,  1.0,   2.0,    3.0,    4.0),
    [], lambda stats, host, monster: cpu_monster_ratio(host, monster))

# --- Row 12. Highest Memory Monster VM to Host Ratio -------------------------------------------------------------
def memory_monster_ratio(
    stats: HostStats, host: HostInventory, monster: MonsterVmSize = DEFAULT_MONSTER_VM
) -> Optional[float]:
    """Memory of the largest VM, against the memory at which a VM becomes a monster on this host."""
    memory = [vm.memory_mb for vm in host.vms if vm.memory_mb]
    dram_kb = dram_capacity_kb(stats)
    if dram_kb is None or not memory:
        return None
    monster_mb = min(monster.ratio_of_dram * dram_kb / 1024.0, monster.memory_min_mb)
    return max(memory) / monster_mb


MEMORY_MONSTER = RiskRow(
    Metric("Highest Memory Monster VM to Host Ratio", None,  0.0,  1.0,   2.0,    3.0,    4.0),
    [], lambda stats, host, monster: memory_monster_ratio(stats, host, monster))


# The rows, in the order of the source table.
ROWS = [
    THREAD_UTILIZATION, IMBALANCE, MEMORY_CONSUMED,
    BALLOONED, ZIP_SWAP, TIERING_LATENCY,
    CPU_RESERVATION, MEMORY_RESERVATION,
    CPU_OVERCOMMIT, MEMORY_OVERCOMMIT,
    CPU_MONSTER, MEMORY_MONSTER,
]
METRICS = [row.metric for row in ROWS]
# Every row is published on the cluster, because none of them exists there as a stat already.
PUBLISHED_METRICS = METRICS
# Every stat asked from VCF Operations for each host: the DRAM capacity, and what each row reads.
HOST_STATS = list(dict.fromkeys(DRAM_STATS + [key for row in ROWS for key in row.stats]))


# =================================================================================================================
# Part 3. The KPI
# =================================================================================================================

def host_risk_values(
    host: HostInventory, stats: HostStats, monster: MonsterVmSize = DEFAULT_MONSTER_VM
) -> Dict[str, Optional[float]]:
    """The value of every row for ONE host. None means "no data"."""
    return {row.metric.name: row.value(stats, host, monster) for row in ROWS}


def cluster_risk_values(
    hosts: List[HostInventory], stats_by_host: Dict[str, HostStats],
    monster: MonsterVmSize = DEFAULT_MONSTER_VM,
) -> Dict[str, Optional[float]]:
    """The value of every row for the cluster: the highest host. None means "no data"."""
    per_host = [host_risk_values(host, stats_by_host.get(host.host_id, {}), monster) for host in hosts]

    cluster_values = {}
    for metric in METRICS:
        host_values = [values[metric.name] for values in per_host if values[metric.name] is not None]
        cluster_values[metric.name] = max(host_values) if host_values else None
    return cluster_values


def collect_cluster_risk_metrics(
    cluster_obj: Object, cluster_name: str, hosts: List[HostInventory], suite_api_client: SuiteApiClient,
    monster: MonsterVmSize = DEFAULT_MONSTER_VM,
) -> Dict[str, HostStats]:
    """Publishes the rows, then the Cluster Risk KPI computed from them.

    hosts holds one HostInventory per ESXi host of the cluster that VCF Operations knows about.
    monster is the Monster VM size from the account settings, see monster_vm_size().
    Returns the host stats it read, {host id: {stat key: value}}, so that Cluster Consumption uses the same
    values without reading them again. Empty when the read failed.
    """
    stats_by_host = {}
    try:
        # One request for all hosts of the cluster.
        stats_by_host = read_latest_stats(suite_api_client, [host.host_id for host in hosts], HOST_STATS)

        values = cluster_risk_values(hosts, stats_by_host, monster)

        no_data = publish_kpi(cluster_obj, GROUP, KPI_KEY, METRICS, PUBLISHED_METRICS, values,
                              higher_is_worse=HIGHER_IS_WORSE).no_data
        if no_data:
            logger.info(f"Cluster Risk for {cluster_name}: no data, so left out: {', '.join(no_data)}")

    except Exception as e:
        # A failure here must not stop the collection of the other cluster data.
        logger.warning(f"Failed to retrieve vSphere Cluster Risk metrics for : {cluster_name} - {repr(e)}")
    return stats_by_host
