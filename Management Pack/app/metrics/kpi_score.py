#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Scoring shared by every KPI (Cluster Performance, VM Performance, ...).

A KPI is one 0-100 % score built from a table of sub-metrics. Each KPI module
holds its own table (a list of Metric rows) and supplies the values. The
scoring itself is here, so it exists once. No API calls here, so it is easy
to test.

How the score works
-------------------
1. Each sub-metric has five limits: the values where its score is 100, 75, 50,
   25 and 0. They split its values into four tiers. Inside a tier the score
   drops in a straight line, by 25 points across the tier:

       tier     value range             score
       green    best    up to green     100 -> 75
       yellow   green   up to yellow     75 -> 50
       orange   yellow  up to orange     50 -> 25
       red      orange  up to zero-at    25 ->  0   (stays 0 beyond zero-at)

2. Its weight depends on its score. It doubles for every 25 points the score
   falls:

       weight = 2 ^ ((100 - score) / 25)

   That is 1 at score 100, 2 at 75, 4 at 50, 8 at 25 and 16 at 0. Between those
   points the weight changes smoothly, so the KPI does not jump when a value
   crosses a limit (issue #18). See docs/concepts/kpi-weights.svg.

3. The KPI is the weighted average of the sub-metric scores:

       KPI = sum(score x weight) / sum(weight)

Why the weight rises as the score falls: with a plain average, one metric in the
red tier would be hidden by nine healthy ones (score ~92). Doubling the weight
as the score falls makes a problem show (score ~62) while still letting the
healthy metrics count.

Direction: most sub-metrics are "lower is better", so their limits go up
(0, 1, 2, 4, 8). A "higher is better" sub-metric, such as free memory, has
limits that go down (1024, 512, 256, 128, 0). Both use the same code.

Green can be a single value: when the green limit equals "best", only that
value is green. Any other value starts in yellow, at 75 with weight 2. Use this
when the source table gives green as one value, such as "0 %".

Missing data: a sub-metric with no data is left out of the KPI. It is never
treated as 0, because 0 usually means "perfect".

Skip when green: the source tables mark some green ranges "Excluded". Being in
green there says nothing about health: dropped packets are rare, and low CPU or
memory utilization is not a sign of good performance. Scoring them 100 every
cycle would give the KPI a free pass that hides the other sub-metrics. A row
with skip_when_green=True is left out of the KPI while its value is green: at or
below best, or below the green limit. It is tested on the value, not on the
weight, which changes smoothly. It counts only when it leaves green. If every sub-metric with data
was left out this way, nothing is wrong, so the KPI is 100.

Used by: every KPI module, such as cluster/cluster_performance_metrics.py and
vm/vm_performance_metrics.py. A change here changes all of them.
Overall approach for all KPIs: metrics/README.md
"""
import math
from typing import Dict, List, NamedTuple, Optional, Tuple


class Metric(NamedTuple):
    name: str               # the one name used everywhere: in the KPI module, in adapter.py and in VCF Operations
    unit: Optional[str]
    best: float             # the score is 100 here, and stays 100 beyond it
    green: float            # the green tier ends here
    yellow: float           # the yellow tier ends here
    orange: float           # the orange tier ends here
    zero_at: float          # the red tier ends here, and the score reaches 0
    skip_when_green: bool = False   # True: left out of the KPI while green, see "Skip when green" above


TIERS = [
    # tier      score at start of tier
    ("green",   100.0),
    ("yellow",  75.0),
    ("orange",  50.0),
    ("red",     25.0),
]
SCORE_DROP_PER_TIER = 25.0


def weight_for_score(score: float) -> float:
    """The weight of a sub-metric with this score: doubles for every 25 points lost."""
    return 2 ** ((100.0 - score) / SCORE_DROP_PER_TIER)


def score_metric(metric: Metric, value: float) -> Tuple[float, float]:
    """Returns (score, weight) for one sub-metric value."""
    score = _score(metric, value)
    return score, weight_for_score(score)


def is_green(metric: Metric, value: float) -> bool:
    """True when the value is in the green tier: at or below best, or below the green limit."""
    if metric.zero_at < metric.best:
        value, best, green = -value, -metric.best, -metric.green
    else:
        best, green = metric.best, metric.green
    return value <= best or value < green


def _score(metric: Metric, value: float) -> float:
    limits = [metric.best, metric.green, metric.yellow, metric.orange, metric.zero_at]
    if metric.zero_at < metric.best:
        # Higher is better. Flip the signs, so the loop below only has to handle limits that go up.
        value = -value
        limits = [-limit for limit in limits]

    # "best", or better than "best", scores 100.
    tier_start = limits[0]
    if value <= tier_start:
        return 100.0

    # Find the tier the value is in. Red is the last tier, so it also takes every value beyond zero-at.
    for (tier_name, score_at_start), tier_end in zip(TIERS, limits[1:], strict=False):
        # A tier with no width, such as green when it is a single value, holds no value. Go to the next one.
        if tier_end == tier_start:
            continue
        if value < tier_end or tier_name == "red":
            # 0.0 at the start of the tier, 1.0 at its end. The cap keeps the score at 0 beyond zero-at.
            distance_into_tier = min((value - tier_start) / (tier_end - tier_start), 1.0)
            return score_at_start - distance_into_tier * SCORE_DROP_PER_TIER
        tier_start = tier_end


def kpi_score(metrics: List[Metric], values: Dict[str, Optional[float]]) -> Optional[float]:
    """Returns the KPI (0-100), or None when no sub-metric has data.

    values maps a sub-metric name to its value. None means "no data".
    """
    total_weighted_score = 0.0
    total_weight = 0.0
    any_data = False

    for metric in metrics:
        value = values.get(metric.name)
        # No data: leave the sub-metric out, so it adds neither score nor weight.
        if value is None:
            continue
        any_data = True
        score, weight = score_metric(metric, value)
        # Skip when green: a rare problem that is not happening gets no free pass. Leave it out too.
        if metric.skip_when_green and is_green(metric, value):
            continue
        total_weighted_score += score * weight
        total_weight += weight

    if total_weight == 0:
        # Every sub-metric with data was green and skipped: nothing is wrong. No data at all: no KPI.
        return 100.0 if any_data else None
    return round(total_weighted_score / total_weight, 2)


# ---------------------------------------------------------------------------
# Small helpers for the sub-metric formulas in the KPI modules.
# ---------------------------------------------------------------------------

def percent(part: float, whole: float) -> Optional[float]:
    """part as a percentage of whole. None when whole is 0 or less, because then there is nothing to divide by."""
    if whole <= 0:
        return None
    return part / whole * 100.0


def has_all(stats: Dict[str, float], stat_keys: List[str]) -> bool:
    """True when every stat a formula needs has data. A formula with a stat missing must return None."""
    return all(key in stats for key in stat_keys)


def percentile_90(numbers: List[float]) -> Optional[float]:
    """The value that 90 % of the numbers are at or below. None when the list is empty.

    Nearest-rank method: sort the numbers and take the one at position 90 % of the count, rounded up.
    With 20 VMs that is the 18th lowest. With fewer than 10 VMs it is the highest, the same as the worst VM.
    """
    if not numbers:
        return None
    position = math.ceil(0.9 * len(numbers))
    return sorted(numbers)[position - 1]


# ---------------------------------------------------------------------------
# Publishing. The same last step for every KPI.
# ---------------------------------------------------------------------------

class PublishedKpi(NamedTuple):
    """What publish_kpi() published for one object."""
    score: Optional[float]      # the KPI as published, or None when no sub-metric had data
    no_data: List[str]          # names of the sub-metrics with no data, left out of the KPI


def publish_kpi(
    obj, group: str, kpi_key: str, metrics: List[Metric], published_metrics: List[Metric],
    values: Dict[str, Optional[float]], higher_is_worse: bool = False,
) -> PublishedKpi:
    """Publishes the sub-metrics and the KPI of one object. Returns the KPI and the sub-metrics with no data.

    obj is the VCF Operations object: a cluster, host or VM. group, kpi_key, metrics and published_metrics
    are the GROUP, KPI_KEY, METRICS and PUBLISHED_METRICS of the KPI module.
    values maps each sub-metric name to its value, None meaning "no data".

    higher_is_worse: publish 100 - score, for a KPI whose name says "higher is worse", such as Cluster Risk
    (100 = maximum risk). The scoring above is unchanged; only the published number is flipped.
    """
    # Drop the sub-metrics with no data, and round the others to two decimals.
    # Round first, so the KPI is computed from exactly the numbers that are published.
    values = {name: round(value, 2) for name, value in values.items() if value is not None}

    # Publish the sub-metrics that the object does not already have as a stat.
    for metric in published_metrics:
        if metric.name in values:
            obj.with_metric(f"vCommunity|{group}|{metric.name}", values[metric.name])

    # Score them all and publish the KPI. No KPI when no sub-metric has data.
    score = kpi_score(metrics, values)
    if score is not None and higher_is_worse:
        score = round(100.0 - score, 2)
    if score is not None:
        obj.with_metric(f"vCommunity|{group}|{kpi_key}", score)

    return PublishedKpi(score, [metric.name for metric in metrics if metric.name not in values])
