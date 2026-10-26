#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Delta Close Count and Cluster Delta Open Count: which changes are counted, and the window they use.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.cluster import periodic_cluster_check as pc
from metrics.world import cluster_close_changes as ccc


def test_close_and_open_are_counted_per_direction():
    previous = {"a": 0.0, "b": 1.0, "c": 0.0, "d": 1.0, "e": 1.0}
    current = {"a": 1.0, "b": 0.0, "c": 0.0, "d": 1.0, "e": 0.0}
    # a: 0 to 1 (close). b: 1 to 0 (open). e: 1 to 0 (open). c and d did not change.
    assert ccc.transition_counts(previous, current) == (1, 2)


def test_a_blank_previous_value_is_not_counted():
    # A new cluster has no earlier Close for Business: not a change from 0 nor from 1.
    assert ccc.transition_counts({}, {"new_closed": 1.0, "new_open": 0.0}) == (0, 0)


def test_a_blank_current_value_is_not_counted():
    # No value in the latest window: not a change to 0 nor to 1.
    assert ccc.transition_counts({"a": 0.0, "b": 1.0}, {}) == (0, 0)


def test_no_change_counts_nothing():
    assert ccc.transition_counts({"a": 0.0, "b": 1.0}, {"a": 0.0, "b": 1.0}) == (0, 0)


def test_last_values_takes_the_last_sample_of_each_cluster():
    samples = {
        "a": {pc.CLOSE_FOR_BUSINESS_KEY: [0.0, 1.0]},
        "b": {pc.CLOSE_FOR_BUSINESS_KEY: []},          # no value: left out
        "c": {"some other stat": [1.0]},               # no Close for Business: left out
    }
    assert ccc.last_values(samples) == {"a": 1.0}


def test_window_is_the_periodic_check_window_for_the_settings():
    # 09:30 UTC, 6-hour period, windows end at 00:00, 06:00, 12:00, 18:00.
    now = datetime(2026, 10, 12, 9, 30, tzinfo=timezone.utc)
    window_end, hours = pc.current_window(now, "00:00", "06")
    assert (window_end, hours) == (datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc), 6)
    # Empty settings: 24 hours, ending at 00:00 UTC.
    window_end, hours = pc.current_window(now, None, None)
    assert (window_end, hours) == (datetime(2026, 10, 12, 0, 0, tzinfo=timezone.utc), 24)


def test_is_due_only_for_a_cluster_with_kpi_data_not_yet_calculated():
    begin, end = 1000, 2000
    kpi = pc.STAT_KEYS[0]
    done = pc.PUBLISHED_KEYS[0]
    # KPI data in the window, nothing calculated: due.
    assert pc.is_due({kpi: 1500.0}, begin, end)
    # Calculated for this window already: not due.
    assert not pc.is_due({kpi: 1500.0, done: 2100.0}, begin, end)
    # KPI data only from before the window: not due, so it is not read every cycle.
    assert not pc.is_due({kpi: 500.0}, begin, end)
    assert not pc.is_due({}, begin, end)
