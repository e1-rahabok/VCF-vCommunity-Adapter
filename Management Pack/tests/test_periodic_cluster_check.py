#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Periodic Cluster Check: the schedule, the worst percent, the rule, and which clusters are due.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.cluster import periodic_cluster_check as pc
from fakes import FakeObject, FakeSuiteApi

NOW = datetime(2026, 10, 12, 9, 30, tzinfo=timezone.utc)


def test_parse_time():
    assert pc.parse_time("06:15") == (6, 15)
    assert pc.parse_time(" 23:59 ") == (23, 59)
    # Empty or invalid: the default, 00:00.
    assert pc.parse_time(None) == (0, 0)
    assert pc.parse_time("") == (0, 0)
    assert pc.parse_time("24:00") == (0, 0)
    assert pc.parse_time("6pm") == (0, 0)


def test_window_ends_at_the_last_time_the_clock_passed_the_setting():
    # 09:30 now: 06:00 today has passed, 12:00 today has not, so yesterday's.
    assert pc.latest_window_end(NOW, 6, 0) == datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)
    assert pc.latest_window_end(NOW, 12, 0) == datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
    assert pc.latest_window_end(NOW, 9, 30) == NOW
    assert pc.window_end_text(NOW) == "2026-10-12 09:30 UTC"


# --- Worst percent -------------------------------------------------------------------------------------------

DAY = [float(n) for n in range(288, 0, -1)]      # 288 five-minute samples: 1 to 288, in any order


def test_percentile_ignores_the_highest_samples():
    # 95th: position ceil(0.95 x 288) = 274.
    assert pc.percentile(DAY, 95) == 274.0
    assert pc.percentile(DAY, 100) == 288.0
    assert pc.percentile([], 95) is None


def test_worst_takes_the_bad_end_of_each_kpi():
    # Higher is worse (Risk, Consumption): the 14 highest samples (5 % of 288) are ignored.
    assert pc.worst(DAY, 5, higher_is_worse=True) == 274.0
    # Higher is better (Performance): the 14 lowest samples are ignored, not the highest.
    assert pc.worst(DAY, 5, higher_is_worse=False) == 15.0
    # 0: the single worst sample.
    assert pc.worst(DAY, 0, higher_is_worse=True) == 288.0
    assert pc.worst(DAY, 0, higher_is_worse=False) == 1.0
    # 50: the middle.
    assert pc.worst(DAY, 50, higher_is_worse=True) == 144.0
    assert pc.worst(DAY, 50, higher_is_worse=False) == 145.0
    assert pc.worst([], 5, higher_is_worse=True) is None


def test_one_bad_sample_in_a_quiet_window_is_ignored():
    # Performance at 90 all day, with one 5-minute dip to 20: the worst 5 % is still 90.
    assert pc.worst([90.0] * 287 + [20.0], 5, higher_is_worse=False) == 90.0
    # With 0 %, the dip decides.
    assert pc.worst([90.0] * 287 + [20.0], 0, higher_is_worse=False) == 20.0


def test_parse_worst_percent():
    assert pc.parse_worst_percent("5") == 5
    assert pc.parse_worst_percent("0") == 0
    assert pc.parse_worst_percent("50") == 50
    assert pc.parse_worst_percent(10) == 10            # as an int parameter may return it
    # Empty or invalid: the default, 5.
    assert pc.parse_worst_percent(None) == 5
    assert pc.parse_worst_percent("") == 5
    assert pc.parse_worst_percent("51") == 5
    assert pc.parse_worst_percent("-1") == 5
    assert pc.parse_worst_percent("2.5") == 5


# --- The rule ------------------------------------------------------------------------------------------------

def test_bands():
    # Performance, higher is better: red below 25, orange below 50, yellow below 75.
    assert [pc.band(value, False) for value in (10.0, 30.0, 60.0, 90.0)] == ["red", "orange", "yellow", "green"]
    # Risk and Consumption, higher is worse: red above 75, orange above 50, yellow above 25.
    assert [pc.band(value, True) for value in (90.0, 70.0, 40.0, 10.0)] == ["red", "orange", "yellow", "green"]


def test_a_value_on_a_limit_belongs_to_the_better_band():
    assert pc.band(25.0, False) == "orange"     # Performance 25 is not red
    assert pc.band(75.0, True) == "orange"      # Risk 75 is not red
    assert pc.band(50.0, False) == "yellow"
    assert pc.band(50.0, True) == "yellow"


def test_close_for_business_when_consumption_or_contention_is_red():
    # decide(performance, risk, consumption)
    assert pc.decide(24.0, 0.0, 0.0) == 1       # Performance red: the VMs already suffer
    assert pc.decide(99.0, 0.0, 76.0) == 1      # Consumption red: the cluster is full


def test_risk_never_closes_a_cluster_on_its_own():
    # Risk is a leading indicator. Red Risk with healthy Consumption and Performance stays open.
    assert pc.decide(99.0, 99.0, 0.0) == 0
    # Only one of Consumption and Performance orange: Risk is not looked at.
    assert pc.decide(40.0, 99.0, 40.0) == 0
    assert pc.decide(60.0, 99.0, 60.0) == 0


def test_risk_decides_when_consumption_and_contention_are_both_orange():
    assert pc.decide(40.0, 60.0, 60.0) == 1     # Risk orange: the threshold of a critical cluster
    assert pc.decide(40.0, 90.0, 60.0) == 1     # Risk red
    assert pc.decide(40.0, 40.0, 60.0) == 0     # Risk yellow
    assert pc.decide(40.0, 10.0, 60.0) == 0     # Risk green
    # Limits: Performance 50 is yellow, so not both orange.
    assert pc.decide(50.0, 60.0, 60.0) == 0
    assert pc.decide(49.99, 50.01, 50.01) == 1


def test_open_when_healthy_or_on_the_red_limit():
    assert pc.decide(95.0, 10.0, 30.0) == 0
    assert pc.decide(25.0, 75.0, 75.0) == 1     # not red, but all three orange
    assert pc.decide(25.0, 0.0, 0.0) == 0       # Performance 25 is orange, Consumption green


def samples(performance, risk, consumption):
    return {pc.CLUSTER_PERFORMANCE_SCORE: performance, pc.CLUSTER_RISK_SCORE: risk,
            pc.CLUSTER_CONSUMPTION_SCORE: consumption}


def test_window_values():
    values = pc.window_values(samples([95.0], [10.0], [40.0]))
    assert values == {pc.PERFORMANCE: 95.0, pc.RISK: 10.0, pc.CONSUMPTION: 40.0, pc.CLOSE_FOR_BUSINESS: 0}


def test_no_close_for_business_when_an_input_has_no_data():
    values = pc.window_values({pc.CLUSTER_RISK_SCORE: [90.0], pc.CLUSTER_PERFORMANCE_SCORE: [95.0]})
    assert values == {pc.PERFORMANCE: 95.0, pc.RISK: 90.0, pc.CONSUMPTION: None, pc.CLOSE_FOR_BUSINESS: None}


# --- Which clusters are due ----------------------------------------------------------------------------------
# At 09:30 with 00:00 and 24 hours, the latest window is 2026-10-11 00:00 to 2026-10-12 00:00.

CLUSTERS = {"ClusterComputeResource": [("cl-1", "cluster-a", "domain-c1"), ("cl-2", "cluster-b", "domain-c2")]}
CLOSE_KEY = f"vCommunity|{pc.GROUP}|{pc.CLOSE_FOR_BUSINESS}"


def ms(*args):
    return datetime(*args, tzinfo=timezone.utc).timestamp() * 1000


AFTER_THIS_WINDOW = ms(2026, 10, 12, 0, 5)      # calculated in the first cycle after the window ended
AFTER_LAST_WINDOW = ms(2026, 10, 11, 0, 5)      # calculated for the window before


def history(performance, risk, consumption, calculated_at=None):
    """KPI samples of one cluster, and its last Close for Business when it was calculated before."""
    stats = samples(performance, risk, consumption)
    if calculated_at is not None:
        stats[CLOSE_KEY] = [0.0]
    return stats


def api_with(calculated, kpi_at=None, **kwargs):
    """Both clusters with KPI data. calculated: {cluster id: when its check metrics were last published}."""
    data = {"cl-1": history([95.0], [10.0, 20.0], [40.0], calculated.get("cl-1")),
            "cl-2": history([20.0], [80.0], [40.0], calculated.get("cl-2"))}
    latest_at = {cluster: {CLOSE_KEY: at} for cluster, at in calculated.items() if at is not None}
    for cluster, at in (kpi_at or {}).items():
        latest_at.setdefault(cluster, {}).update({key: at for key in pc.STAT_KEYS})
    return FakeSuiteApi(resources=CLUSTERS, samples=data, latest_at=latest_at, **kwargs)


HISTORY = {"cl-1": samples([95.0], [10.0, 20.0], [40.0]), "cl-2": samples([20.0], [80.0], [40.0])}


def test_only_clusters_not_calculated_for_the_latest_window_are_due():
    api = api_with({"cl-1": AFTER_THIS_WINDOW, "cl-2": AFTER_LAST_WINDOW})
    results = pc.read_periodic_cluster_check(api, "ai-1", "00:00", NOW)
    assert list(results) == ["domain-c2"]
    assert results["domain-c2"].window_end == "2026-10-12 00:00 UTC"
    # The clusters of this vCenter only.
    assert api.resource_queries[0]["adapterInstanceId"] == ["ai-1"]


def test_a_cluster_never_calculated_is_due():
    assert set(pc.read_periodic_cluster_check(api_with({}), "ai-1", "00:00", NOW)) == {"domain-c1", "domain-c2"}


def test_nothing_due_reads_no_history():
    api = api_with({"cl-1": AFTER_THIS_WINDOW, "cl-2": AFTER_THIS_WINDOW})
    assert pc.read_periodic_cluster_check(api, "ai-1", "00:00", NOW) == {}
    assert "api/resources/stats/query" not in api.paths


def test_a_cluster_without_kpi_data_in_the_window_is_not_due():
    # Its KPIs stopped before the window began: nothing to calculate, so it is not read every cycle.
    api = api_with({}, kpi_at={"cl-1": ms(2026, 10, 10, 12, 0), "cl-2": ms(2026, 10, 10, 12, 0)})
    assert pc.read_periodic_cluster_check(api, "ai-1", "00:00", NOW) == {}


def test_a_changed_setting_applies_from_the_next_window():
    # Calculated for this window already: a new worst percent does not recalculate it.
    api = api_with({"cl-1": AFTER_THIS_WINDOW, "cl-2": AFTER_THIS_WINDOW})
    assert pc.read_periodic_cluster_check(api, "ai-1", "00:00", NOW, worst_percent_setting="10") == {}
    # A cluster that is due uses the new setting.
    results = pc.read_periodic_cluster_check(api_with({}), "ai-1", "00:00", NOW, worst_percent_setting="10")
    assert results["domain-c1"].worst_percent == 10


def test_due_clusters_are_taken_in_turn_when_there_are_more_than_the_limit():
    # 5 due clusters, 2 per cycle. A cluster that stays due without result does not block the others.
    due = ["a", "b", "c", "d", "e"]
    end = datetime(2026, 10, 12, 0, 0, tzinfo=timezone.utc)
    cycles = [pc.this_cycle(due, end + timedelta(minutes=5 * n + 1), end, limit=2) for n in range(3)]
    assert cycles == [["a", "b"], ["c", "d"], ["e", "a"]]
    # Every due cluster had its turn within ceil(5 / 2) = 3 cycles.
    assert set(sum(cycles, [])) == set(due)
    # Up to the limit, all of them every cycle.
    assert pc.this_cycle(["a", "b"], end, end, limit=2) == ["a", "b"]


def test_unreadable_timestamps_calculate_nothing():
    # Without them every cluster would look due: wait for the next cycle instead.
    api = api_with({}, status_code=500)
    assert pc.read_periodic_cluster_check(api, "ai-1", "00:00", NOW) == {}


def test_at_most_max_clusters_per_cycle(monkeypatch):
    monkeypatch.setattr(pc, "MAX_CLUSTERS_PER_CYCLE", 1)
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY)
    assert list(pc.read_periodic_cluster_check(api, "ai-1", "00:00", NOW)) == ["domain-c1"]


def test_failed_history_request_leaves_the_clusters_due():
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY, status_code=500)
    assert pc.read_periodic_cluster_check(api, "ai-1", "00:00", NOW) == {}


def test_publish():
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY)
    results = pc.read_periodic_cluster_check(api, "ai-1", "00:00", NOW)
    cluster = FakeObject("cluster-b")
    pc.publish(cluster, results["domain-c2"])
    group = f"vCommunity|{pc.GROUP}"
    # The values are metrics: numbers produced once per period.
    assert cluster.metrics == {
        f"{group}|Worst Cluster Performance": 20.0,
        f"{group}|Worst Cluster Risk": 80.0,
        f"{group}|Worst Cluster Consumption": 40.0,
        f"{group}|Close for Business": 1,               # Performance 20 is red
    }
    # No properties: the metrics' own timestamps say the cluster was calculated for this window.
    assert cluster.properties == {}


def test_not_due_publishes_nothing():
    cluster = FakeObject("cluster-a")
    pc.publish(cluster, None)
    assert cluster.properties == {}
    assert cluster.metrics == {}


def test_the_24_hours_end_at_the_set_time():
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY)
    sent = []
    original = api.post
    api.post = lambda path, json: (sent.append(json), original(path, json))[1]
    pc.read_periodic_cluster_check(api, "ai-1", "06:00", NOW)
    history = [request for request in sent if "begin" in request][0]
    end = int(datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc).timestamp() * 1000)
    assert history["end"] == end
    assert history["begin"] == end - 24 * 3600 * 1000
    assert history["intervalQuantifier"] == 5
    assert history["statKey"] == pc.STAT_KEYS


# --- Period --------------------------------------------------------------------------------------------------

def test_parse_period():
    assert pc.parse_period("6") == 6
    assert pc.parse_period(None) == 24
    assert pc.parse_period("") == 24
    assert pc.parse_period("5") == 24          # not in the list: the default


def test_window_ends_every_period_from_the_set_time():
    # 09:30 now. Set time 00:00, every 6 hours: ends at 00:00, 06:00, 12:00, 18:00. Latest: 06:00.
    assert pc.latest_window_end(NOW, 0, 0, 6) == datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)
    # Every hour, from 00:15: latest 09:15.
    assert pc.latest_window_end(NOW, 0, 15, 1) == datetime(2026, 10, 12, 9, 15, tzinfo=timezone.utc)
    # Set time 10:00, every 8 hours: ends at 02:00, 10:00, 18:00. Latest: 02:00.
    assert pc.latest_window_end(NOW, 10, 0, 8) == datetime(2026, 10, 12, 2, 0, tzinfo=timezone.utc)
    # 24 hours is unchanged.
    assert pc.latest_window_end(NOW, 12, 0, 24) == datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


def test_the_window_is_as_long_as_the_period():
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY)
    sent = []
    original = api.post
    api.post = lambda path, json: (sent.append(json), original(path, json))[1]
    results = pc.read_periodic_cluster_check(api, "ai-1", "00:00", NOW, period_setting="6")
    history = [request for request in sent if "begin" in request][0]
    end = int(datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc).timestamp() * 1000)
    assert history["end"] == end
    assert history["begin"] == end - 6 * 3600 * 1000
    assert results["domain-c2"].window_hours == 6


def test_period_drop_down_sorts_like_numbers():
    # VCF Operations sorts the drop-down by stored value, as text. The labels are kept in the same order.
    values = [value for value, _ in pc.PERIOD_CHOICES]
    labels = [label for _, label in pc.PERIOD_CHOICES]
    assert sorted(values) == values == pc.PERIOD_HOURS
    assert [int(value) for value in values] == [1, 2, 4, 6, 8, 12, 24]
    assert sorted(labels) == labels
    assert labels[0] == "01 hour" and labels[-1] == "24 hours"
    assert pc.DEFAULT_PERIOD in values


def test_parse_period_accepts_values_without_the_zero():
    assert pc.parse_period("06") == 6
    assert pc.parse_period("6") == 6
    assert pc.parse_period("1") == 1
    assert pc.parse_period("24") == 24
    assert pc.parse_period("006") == 6
    assert pc.parse_period("x") == 24
