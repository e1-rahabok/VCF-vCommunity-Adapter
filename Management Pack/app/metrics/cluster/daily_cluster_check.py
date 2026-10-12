#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Daily Cluster Check: once a day, per cluster, whether it is closed for business (full for new VMs).

What it is
----------
Once a day, at the time set in the account's Advanced Settings ("Daily Cluster Check Time", UTC), every cluster
gets these properties, under vCommunity|Daily Cluster Check:

    95th Percentile Cluster Risk             of Cluster Risk Score (higher is worse), over the 24 hours
    95th Percentile Cluster Performance      of Cluster Performance Score (higher is better), over the 24 hours
    99th Percentile Capacity Utilization     max(99th percentile of CPU utilization, of memory utilization)
    Close for Business                       1 = the cluster is full, do not place new VMs. 0 = open. See decide().
    Window End                               the end of the 24 hours, such as "2026-10-12 00:00 UTC"

The 24 hours end at the set time, not when the calculation runs. So every cluster has the same window, even
when it is calculated a few cycles later.

How it runs
-----------
The pack collects every 5 minutes. Each cycle, the cluster collection reads the Window End property of its
clusters. A cluster is due when it does not have the latest window end yet. At most MAX_CLUSTERS_PER_CYCLE due
clusters are calculated per cycle, the rest in the next cycles, so the 24-hour history is not read all at once.
A cluster whose history could not be read stays due, and is tried again in the next cycle.

No state is kept in the adapter: the Window End property, stored in VCF Operations, is the state. A restart or
an upgrade of the pack does not lose it.

Inputs, all from VCF Operations: the 5-minute history of the four stats in STAT_KEYS.
Docs: docs/daily-cluster-check.md
"""
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, NamedTuple, Optional, Tuple
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from metrics.cluster import cluster_performance_metrics, cluster_risk_metrics
from utils.ops_stats import query_resources, read_latest_properties, read_stat_history

logger = logging.getLogger(__name__)

GROUP = "Daily Cluster Check"

# Account setting (Advanced Settings): the time of day, in UTC, when the 24 hours end.
TIME_SETTING = "daily_cluster_check_time"
DEFAULT_TIME = "00:00"

# The inputs, as stored in VCF Operations.
CLUSTER_RISK_SCORE = f"vCommunity|{cluster_risk_metrics.GROUP}|{cluster_risk_metrics.KPI_KEY}"
CLUSTER_PERFORMANCE_SCORE = f"vCommunity|{cluster_performance_metrics.GROUP}|{cluster_performance_metrics.KPI_KEY}"
# PLACEHOLDER: the CPU and memory utilization (%) stat keys of a cluster are still to be supplied.
# Until then they return no data, so Capacity Utilization and Close for Business are not published.
CPU_UTILIZATION = "PLACEHOLDER|CPU Utilization"
MEMORY_UTILIZATION = "PLACEHOLDER|Memory Utilization"
STAT_KEYS = [CLUSTER_RISK_SCORE, CLUSTER_PERFORMANCE_SCORE, CPU_UTILIZATION, MEMORY_UTILIZATION]

# The published properties.
RISK = "95th Percentile Cluster Risk"
PERFORMANCE = "95th Percentile Cluster Performance"
UTILIZATION = "99th Percentile Capacity Utilization"
CLOSE_FOR_BUSINESS = "Close for Business"
WINDOW_END = "Window End"
WINDOW_END_KEY = f"vCommunity|{GROUP}|{WINDOW_END}"

# The limits of decide(), in %. All comparisons are strict: a value equal to a limit does not cross it.
FULL_UTILIZATION = 95.0          # rule 1: Capacity Utilization above this
POOR_PERFORMANCE = 25.0          # rule 1: Cluster Performance below this
HIGH_UTILIZATION = 75.0          # rule 2: Capacity Utilization above this, and
LOW_PERFORMANCE = 50.0           #         Cluster Performance below this, and
HIGH_RISK = 75.0                 #         Cluster Risk above this

# Load on VCF Operations. A day of 5-minute samples is 288 per stat, 4 stats per cluster.
MAX_CLUSTERS_PER_CYCLE = 500
CLUSTERS_PER_REQUEST = 100

WINDOW = timedelta(hours=24)


class DailyResult(NamedTuple):
    """What is published on one cluster. A value of None is not published: it had no data."""
    values: Dict[str, Optional[float]]     # RISK, PERFORMANCE, UTILIZATION, CLOSE_FOR_BUSINESS
    window_end: str


# ---------------------------------------------------------------------------
# Schedule. No API calls here, so it is easy to test.
# ---------------------------------------------------------------------------

def parse_time(text: Optional[str]) -> Tuple[int, int]:
    """"HH:MM" -> (hour, minute). An empty or invalid setting falls back to DEFAULT_TIME, with a warning."""
    try:
        hour, minute = (int(part) for part in (text or "").strip().split(":"))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except ValueError:
        pass
    if text:
        logger.warning(f"Daily Cluster Check Time '{text}' is not HH:MM. Using {DEFAULT_TIME} UTC.")
    return parse_time(DEFAULT_TIME)


def latest_window_end(now: datetime, hour: int, minute: int) -> datetime:
    """The last time the clock passed hour:minute UTC, at or before now: today's, or else yesterday's."""
    today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return today if today <= now else today - timedelta(days=1)


def window_end_text(window_end: datetime) -> str:
    return window_end.strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------------------
# Calculation. No API calls here either.
# ---------------------------------------------------------------------------

def percentile(samples: List[float], percent: float) -> Optional[float]:
    """The value that percent % of the samples are at or below. None when there are none.

    Nearest-rank method, as percentile_90() in metrics/vm_contention.py: sort the samples and take the one at
    position percent % of the count, rounded up. With 288 samples, the 95th percentile is the 274th lowest (the
    14 highest are ignored), and the 99th is the 286th lowest (the 2 highest are ignored).
    """
    if not samples:
        return None
    position = math.ceil(percent / 100.0 * len(samples))
    return sorted(samples)[position - 1]


def decide(risk: float, performance: float, utilization: float) -> int:
    """Close for Business: 1 when the cluster is full for new VMs, else 0.

    1. Full or slow: Capacity Utilization above 95, or Cluster Performance below 25.
    2. Busy, slow and at risk, all three: Capacity Utilization above 75, Cluster Performance below 50,
       and Cluster Risk above 75.
    """
    if utilization > FULL_UTILIZATION or performance < POOR_PERFORMANCE:
        return 1
    if utilization > HIGH_UTILIZATION and performance < LOW_PERFORMANCE and risk > HIGH_RISK:
        return 1
    return 0


def daily_values(samples: Dict[str, List[float]]) -> Dict[str, Optional[float]]:
    """The published values of one cluster, from its 24 hours of samples. None means "no data"."""
    risk = percentile(samples.get(CLUSTER_RISK_SCORE, []), 95)
    performance = percentile(samples.get(CLUSTER_PERFORMANCE_SCORE, []), 95)
    cpu = percentile(samples.get(CPU_UTILIZATION, []), 99)
    memory = percentile(samples.get(MEMORY_UTILIZATION, []), 99)
    utilization = max(cpu, memory) if cpu is not None and memory is not None else None

    # Close for Business only when all three are there. A missing value is never taken as 0.
    inputs = [risk, performance, utilization]
    close = decide(risk, performance, utilization) if None not in inputs else None
    return {RISK: risk, PERFORMANCE: performance, UTILIZATION: utilization, CLOSE_FOR_BUSINESS: close}


# ---------------------------------------------------------------------------
# Reading from VCF Operations, and publishing.
# ---------------------------------------------------------------------------

def read_daily_cluster_check(
    suite_api_client: SuiteApiClient, adapter_instance_id: str, time_setting: Optional[str],
    now: Optional[datetime] = None,
) -> Dict[str, DailyResult]:
    """{cluster MoRef id: DailyResult} for the clusters of this vCenter that are due this cycle.

    Empty when no cluster is due: the properties already published stay in VCF Operations.
    """
    now = now or datetime.now(timezone.utc)
    window_end = latest_window_end(now, *parse_time(time_setting))
    end_text = window_end_text(window_end)

    clusters = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "ClusterComputeResource", adapter_instance_id)
    stored = read_latest_properties(suite_api_client, [cluster.id for cluster in clusters], [WINDOW_END_KEY])
    due = [cluster for cluster in clusters if stored.get(cluster.id, {}).get(WINDOW_END_KEY) != end_text]
    if not due:
        return {}
    due = sorted(due, key=lambda cluster: cluster.id)[:MAX_CLUSTERS_PER_CYCLE]
    logger.info(f"Daily Cluster Check: {len(due)} of {len(clusters)} clusters due for the 24 hours to {end_text}.")

    end_ms = int(window_end.timestamp() * 1000)
    begin_ms = int((window_end - WINDOW).timestamp() * 1000)
    failed: List[str] = []
    history = read_stat_history(suite_api_client, [cluster.id for cluster in due], STAT_KEYS,
                                begin_ms, end_ms, CLUSTERS_PER_REQUEST, failed)

    results = {}
    for cluster in due:
        # Not read: leave it due, so the next cycle tries again.
        if cluster.id in failed:
            continue
        results[cluster.moid] = DailyResult(daily_values(history.get(cluster.id, {})), end_text)
    return results


def publish(cluster_obj, daily: Optional[DailyResult]) -> None:
    """Publishes the Daily Cluster Check properties of one cluster. Nothing when it is not due this cycle."""
    if daily is None:
        return
    for name, value in daily.values.items():
        if value is not None:
            cluster_obj.with_property(f"vCommunity|{GROUP}|{name}", round(value, 2))
    # Last, and also without data: the cluster was calculated for this window, so it is not due again.
    cluster_obj.with_property(WINDOW_END_KEY, daily.window_end)
