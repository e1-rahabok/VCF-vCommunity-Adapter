#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Periodic Cluster Check: once per period, per cluster, whether it is closed for business (full for new VMs).

What it is
----------
Once per period, every cluster gets these metrics, under vCommunity|Periodic Cluster Check:

    Worst Cluster Performance     of Cluster Performance Score (higher is better): its low end over the period
    Worst Cluster Risk            of Cluster Risk Score (higher is worse): its high end over the period
    Worst Cluster Consumption     of Cluster Consumption Score (higher is worse): its high end over the period
    Close for Business            1 = the cluster is full, do not place new VMs. 0 = open. See decide().

"Worst" is the value with only the worst N % of the period's samples beyond it: the (100 - N)th percentile
of Risk and Consumption, the Nth percentile of Performance. See worst().

Three account settings (Advanced Settings):
    Cluster Check Period         1, 2, 4, 6, 8, 12 or 24 hours (default 24). Each one divides a day, so the
                                 windows fall at the same times every day.
    Cluster Check Time           a time of day, HH:MM in UTC (default 00:00). One window ends at that time; the
                                 others every period from it. With 6 hours and 00:00: windows end at 00:00,
                                 06:00, 12:00, 18:00.
    Cluster Check Worst Percent  0 to 50 (default 5). 0 is the single worst sample of the period.

A window ends at a fixed time, not when the calculation runs. So every cluster has the same window, even
when it is calculated a few cycles later. The calculation covers the period that just ended: each window is
as long as the period, so every hour is covered once.

How it runs
-----------
The pack collects every 5 minutes. Each cycle, the cluster collection reads the time of the latest sample of
the check's own metrics, and of the three KPIs, for all its clusters. A cluster is due when:
    - its latest check metric is older than the latest window end: not yet calculated for that window, and
    - a KPI has a sample at or after the start of that window: there is something to calculate.
The second condition keeps a cluster without any KPI from being due, and read, every cycle.
At most MAX_CLUSTERS_PER_CYCLE due clusters are calculated per cycle, the rest in the next cycles, so the
history is not read all at once. A cluster whose history could not be read stays due, and is tried again.

No state is kept, in the adapter or as properties: the timestamps of the published metrics are the state. A
restart or an upgrade of the pack does not lose it. A changed setting applies from the next window.

Inputs, all from VCF Operations: the 5-minute history of the three KPIs in STAT_KEYS.
Docs: docs/reference/metrics/periodic-cluster-check.md
"""
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, NamedTuple, Optional, Tuple
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from metrics.cluster import cluster_performance_metrics, cluster_risk_metrics, cluster_consumption_metrics
from utils.ops_stats import query_resources, read_latest_timestamps, read_stat_history

logger = logging.getLogger(__name__)

GROUP = "Periodic Cluster Check"

# Account setting (Advanced Settings): the time of day, in UTC, when a window ends.
TIME_SETTING = "periodic_cluster_check_time"
DEFAULT_TIME = "00:00"
# Account setting (Advanced Settings): the length of the window, which is also how often it is calculated.
PERIOD_SETTING = "cluster_check_period_hours"
# The stored values of the Advanced Settings drop-down. VCF Operations sorts the drop-down by stored value,
# as text, so they are zero-padded: "01" ... "24" sort as 1 ... 24, not as "1", "12", "2", "24".
# The labels are padded the same way, in case a version sorts by label.
PERIOD_HOURS = ["01", "02", "04", "06", "08", "12", "24"]     # each divides 24
PERIOD_CHOICES = [(hours, f"{hours} hour{'s' if hours != '01' else ''}") for hours in PERIOD_HOURS]
DEFAULT_PERIOD = "24"
# Account setting (Advanced Settings): the share of the period's samples, at its worst end, that is ignored.
# Above 50 makes no sense: it would summarise the period by its better half.
WORST_PERCENT_SETTING = "cluster_check_worst_percent"
DEFAULT_WORST_PERCENT = 5
MAX_WORST_PERCENT = 50

# The inputs, as stored in VCF Operations: the three cluster KPIs, each 0-100 %.
CLUSTER_PERFORMANCE_SCORE = f"vCommunity|{cluster_performance_metrics.GROUP}|{cluster_performance_metrics.KPI_KEY}"
CLUSTER_RISK_SCORE = f"vCommunity|{cluster_risk_metrics.GROUP}|{cluster_risk_metrics.KPI_KEY}"
CLUSTER_CONSUMPTION_SCORE = f"vCommunity|{cluster_consumption_metrics.GROUP}|{cluster_consumption_metrics.KPI_KEY}"
STAT_KEYS = [CLUSTER_PERFORMANCE_SCORE, CLUSTER_RISK_SCORE, CLUSTER_CONSUMPTION_SCORE]

# The published metrics.
PERFORMANCE = "Worst Cluster Performance"
RISK = "Worst Cluster Risk"
CONSUMPTION = "Worst Cluster Consumption"
CLOSE_FOR_BUSINESS = "Close for Business"
PUBLISHED_KEYS = [f"vCommunity|{GROUP}|{name}" for name in (PERFORMANCE, RISK, CONSUMPTION, CLOSE_FOR_BUSINESS)]

# Each input: (published metric, its stat, True when higher is worse).
INPUTS = [
    (PERFORMANCE, CLUSTER_PERFORMANCE_SCORE, False),
    (RISK, CLUSTER_RISK_SCORE, cluster_risk_metrics.HIGHER_IS_WORSE),
    (CONSUMPTION, CLUSTER_CONSUMPTION_SCORE, cluster_consumption_metrics.HIGHER_IS_WORSE),
]

# The bands of every KPI, on its health: the value itself when higher is better, 100 minus it when higher is
# worse. A value on a limit belongs to the better band: Performance of exactly 25 is orange, not red.
RED_BELOW = 25.0
ORANGE_BELOW = 50.0
YELLOW_BELOW = 75.0

# Load on VCF Operations. A day of 5-minute samples is 288 per stat, 3 stats per cluster.
MAX_CLUSTERS_PER_CYCLE = 500
CLUSTERS_PER_REQUEST = 100


class PeriodicResult(NamedTuple):
    """What is published on one cluster. A value of None is not published: it had no data."""
    values: Dict[str, Optional[float]]     # PERFORMANCE, RISK, CONSUMPTION, CLOSE_FOR_BUSINESS
    window_end: str                        # for the log, such as "2026-10-12 00:00 UTC"
    window_hours: int = 24
    worst_percent: int = DEFAULT_WORST_PERCENT


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
        logger.warning(f"Cluster Check Time '{text}' is not HH:MM. Using {DEFAULT_TIME} UTC.")
    return parse_time(DEFAULT_TIME)


def parse_period(text: Optional[str]) -> int:
    """The period in hours. An empty or unknown setting falls back to DEFAULT_PERIOD, with a warning.

    "6" and "06" are both 6: accounts saved with version 0.1.1 or earlier store the hours without the zero.
    """
    value = (text or "").strip()
    if value.isdigit() and f"{int(value):02d}" in PERIOD_HOURS:
        return int(value)
    if value:
        logger.warning(f"Cluster Check Period '{text}' is not one of {', '.join(PERIOD_HOURS)}. "
                       f"Using {DEFAULT_PERIOD} hours.")
    return int(DEFAULT_PERIOD)


def parse_worst_percent(text) -> int:
    """The worst percent, 0 to MAX_WORST_PERCENT. An empty or invalid setting falls back to
    DEFAULT_WORST_PERCENT, with a warning."""
    value = str(text if text is not None else "").strip()
    if value.isdigit() and int(value) <= MAX_WORST_PERCENT:
        return int(value)
    if value:
        logger.warning(f"Cluster Check Worst Percent '{text}' is not a whole number from 0 to {MAX_WORST_PERCENT}. "
                       f"Using {DEFAULT_WORST_PERCENT}.")
    return DEFAULT_WORST_PERCENT


def latest_window_end(now: datetime, hour: int, minute: int, period_hours: int = 24) -> datetime:
    """The latest window end at or before now. Windows end at hour:minute UTC and every period_hours from it.

    With 24 hours: today's hour:minute, or else yesterday's. period_hours divides 24, so the ends are the same
    every day.
    """
    anchor = now.replace(hour=hour, minute=minute, second=0, microsecond=0) - timedelta(days=1)
    period = timedelta(hours=period_hours)
    return anchor + period * ((now - anchor) // period)


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
    return sorted(samples)[max(position, 1) - 1]


def worst(samples: List[float], worst_percent: int, higher_is_worse: bool) -> Optional[float]:
    """The value with only the worst worst_percent % of the samples beyond it. None when there are none.

    Higher is worse: the (100 - worst_percent)th percentile. Higher is better: the worst_percent-th percentile,
    taken as the same rank from the low end. 0 is the single worst sample. With 288 samples and 5, the 14
    worst samples (70 minutes) are ignored.
    """
    if not samples:
        return None
    if higher_is_worse:
        return percentile(samples, 100 - worst_percent)
    return -percentile([-sample for sample in samples], 100 - worst_percent)


def band(value: float, higher_is_worse: bool) -> str:
    """"green", "yellow", "orange" or "red", by the KPI bands on the value's health (RED_BELOW and above)."""
    health = 100.0 - value if higher_is_worse else value
    if health < RED_BELOW:
        return "red"
    if health < ORANGE_BELOW:
        return "orange"
    if health < YELLOW_BELOW:
        return "yellow"
    return "green"


def decide(performance: float, risk: float, consumption: float) -> int:
    """Close for Business: 1 when the cluster is full for new VMs, else 0.

    1. Consumption is red, or Performance (contention) is red.
    2. Consumption and Performance are both orange, and Risk is orange or red.

    Risk is a leading indicator: it never closes a cluster on its own. Orange is the Risk threshold of a
    critical (production) cluster, used for every cluster.
    """
    performance_band = band(performance, higher_is_worse=False)
    risk_band = band(risk, cluster_risk_metrics.HIGHER_IS_WORSE)
    consumption_band = band(consumption, cluster_consumption_metrics.HIGHER_IS_WORSE)
    if "red" in (performance_band, consumption_band):
        return 1
    if performance_band == consumption_band == "orange" and risk_band in ("orange", "red"):
        return 1
    return 0


def window_values(samples: Dict[str, List[float]], worst_percent: int = DEFAULT_WORST_PERCENT
                  ) -> Dict[str, Optional[float]]:
    """The published values of one cluster, from the samples of its window. None means "no data"."""
    values = {name: worst(samples.get(stat, []), worst_percent, higher_is_worse)
              for name, stat, higher_is_worse in INPUTS}

    # Close for Business only when all three are there. A missing value is never taken as 0.
    inputs = [values[PERFORMANCE], values[RISK], values[CONSUMPTION]]
    values[CLOSE_FOR_BUSINESS] = decide(*inputs) if None not in inputs else None
    return values


# ---------------------------------------------------------------------------
# Reading from VCF Operations, and publishing.
# ---------------------------------------------------------------------------

def read_periodic_cluster_check(
    suite_api_client: SuiteApiClient, adapter_instance_id: str, time_setting: Optional[str],
    now: Optional[datetime] = None, period_setting: Optional[str] = None, worst_percent_setting=None,
) -> Dict[str, PeriodicResult]:
    """{cluster MoRef id: PeriodicResult} for the clusters of this vCenter that are due this cycle.

    Empty when no cluster is due: the metrics already published for the window stay in VCF Operations.
    """
    now = now or datetime.now(timezone.utc)
    period_hours = parse_period(period_setting)
    worst_percent = parse_worst_percent(worst_percent_setting)
    window_end = latest_window_end(now, *parse_time(time_setting), period_hours)
    end_text = window_end_text(window_end)

    end_ms = int(window_end.timestamp() * 1000)
    begin_ms = int((window_end - timedelta(hours=period_hours)).timestamp() * 1000)

    clusters = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "ClusterComputeResource", adapter_instance_id)
    latest = read_latest_timestamps(suite_api_client, [cluster.id for cluster in clusters], PUBLISHED_KEYS + STAT_KEYS)
    if latest is None:
        # Without the timestamps, every cluster would look due. Wait for the next cycle instead.
        logger.warning("Periodic Cluster Check: could not read which clusters are calculated. Trying next cycle.")
        return {}

    def is_due(cluster) -> bool:
        timestamps = latest.get(cluster.id, {})
        calculated = max((timestamps.get(key, 0.0) for key in PUBLISHED_KEYS), default=0.0)
        has_kpi_data = any(timestamps.get(key, 0.0) >= begin_ms for key in STAT_KEYS)
        return calculated < end_ms and has_kpi_data

    due = [cluster for cluster in clusters if is_due(cluster)]
    if not due:
        return {}
    due = sorted(due, key=lambda cluster: cluster.id)[:MAX_CLUSTERS_PER_CYCLE]
    logger.info(f"Periodic Cluster Check: {len(due)} of {len(clusters)} clusters due for the {period_hours} hours "
                f"to {end_text}, worst {worst_percent} %.")
    failed: List[str] = []
    history = read_stat_history(suite_api_client, [cluster.id for cluster in due], STAT_KEYS,
                                begin_ms, end_ms, CLUSTERS_PER_REQUEST, failed)

    results = {}
    for cluster in due:
        # Not read: leave it due, so the next cycle tries again.
        if cluster.id in failed:
            continue
        samples = history.get(cluster.id, {})
        values = window_values(samples, worst_percent)
        results[cluster.moid] = PeriodicResult(values, end_text, period_hours, worst_percent)
        if values[CLOSE_FOR_BUSINESS] is None:
            counts = ", ".join(f"{key.split('|')[-1]}: {len(samples.get(key, []))}" for key in STAT_KEYS)
            logger.info(f"Periodic Cluster Check of {cluster.name}: no Close for Business for the window to "
                        f"{end_text} - samples in the window: {counts}")
    published = sum(1 for result in results.values() if result.values[CLOSE_FOR_BUSINESS] is not None)
    logger.info(f"Periodic Cluster Check: Close for Business set on {published} of {len(results)} due clusters "
                f"for the {period_hours} hours to {end_text}.")
    return results


def publish(cluster_obj, result: Optional[PeriodicResult]) -> None:
    """Publishes the Periodic Cluster Check metrics of one cluster. Nothing when it is not due this cycle.

    The values are metrics: numbers produced once per period, a fixed interval. Their timestamp is also how the
    next cycles know the cluster was calculated for this window.
    """
    if result is None:
        return
    for name, value in result.values.items():
        if value is not None:
            cluster_obj.with_metric(f"vCommunity|{GROUP}|{name}", round(value, 2))
