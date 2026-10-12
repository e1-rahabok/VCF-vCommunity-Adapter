#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Daily Cluster Check: the schedule, the 95th percentile, and which clusters are due.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.cluster import daily_cluster_check as dc
from fakes import FakeObject, FakeSuiteApi

NOW = datetime(2026, 10, 12, 9, 30, tzinfo=timezone.utc)


def test_parse_time():
    assert dc.parse_time("06:15") == (6, 15)
    assert dc.parse_time(" 23:59 ") == (23, 59)
    # Empty or invalid: the default, 00:00.
    assert dc.parse_time(None) == (0, 0)
    assert dc.parse_time("") == (0, 0)
    assert dc.parse_time("24:00") == (0, 0)
    assert dc.parse_time("6pm") == (0, 0)


def test_window_ends_at_the_last_time_the_clock_passed_the_setting():
    # 09:30 now: 06:00 today has passed, 12:00 today has not, so yesterday's.
    assert dc.latest_window_end(NOW, 6, 0) == datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)
    assert dc.latest_window_end(NOW, 12, 0) == datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
    assert dc.latest_window_end(NOW, 9, 30) == NOW
    assert dc.window_end_text(NOW) == "2026-10-12 09:30 UTC"


def test_percentile_ignores_the_highest_samples():
    day = [float(n) for n in range(288, 0, -1)]
    # 95th: position ceil(0.95 x 288) = 274. 99th: position ceil(0.99 x 288) = 286.
    assert dc.percentile(day, 95) == 274.0
    assert dc.percentile(day, 99) == 286.0
    # One spike in a quiet day is ignored.
    assert dc.percentile([1.0] * 287 + [50.0], 95) == 1.0
    assert dc.percentile([], 95) is None


def samples(risk, performance, cpu, memory):
    return {dc.CLUSTER_RISK_SCORE: risk, dc.CLUSTER_PERFORMANCE_SCORE: performance,
            dc.CPU_UTILIZATION: cpu, dc.MEMORY_UTILIZATION: memory}


def test_utilization_is_the_higher_of_cpu_and_memory():
    values = dc.daily_values(samples([10.0], [95.0], [40.0], [70.0]))
    assert values == {dc.RISK: 10.0, dc.PERFORMANCE: 95.0, dc.UTILIZATION: 70.0, dc.CLOSE_FOR_BUSINESS: 0}


def test_close_for_business_rules():
    # decide(risk, performance, utilization)
    # Rule 1: utilization above 95, or performance below 25.
    assert dc.decide(0.0, 99.0, 96.0) == 1
    assert dc.decide(0.0, 24.0, 10.0) == 1
    # Rule 2: utilization above 75 AND performance below 50 AND risk above 75.
    assert dc.decide(80.0, 40.0, 80.0) == 1
    assert dc.decide(70.0, 40.0, 80.0) == 0      # risk not above 75
    assert dc.decide(80.0, 60.0, 80.0) == 0      # performance not below 50
    assert dc.decide(80.0, 40.0, 70.0) == 0      # utilization not above 75
    # Healthy.
    assert dc.decide(10.0, 95.0, 50.0) == 0


def test_limits_are_strict():
    assert dc.decide(0.0, 99.0, 95.0) == 0       # 95 is not above 95
    assert dc.decide(0.0, 25.0, 10.0) == 0       # 25 is not below 25
    assert dc.decide(75.0, 49.0, 80.0) == 0      # 75 is not above 75


def test_no_close_for_business_when_an_input_has_no_data():
    values = dc.daily_values({dc.CLUSTER_RISK_SCORE: [90.0], dc.CLUSTER_PERFORMANCE_SCORE: [95.0]})
    assert values == {dc.RISK: 90.0, dc.PERFORMANCE: 95.0, dc.UTILIZATION: None, dc.CLOSE_FOR_BUSINESS: None}


CLUSTERS = {"ClusterComputeResource": [("cl-1", "cluster-a", "domain-c1"), ("cl-2", "cluster-b", "domain-c2")]}
HISTORY = {"cl-1": samples([10.0, 20.0], [95.0], [40.0], [70.0]), "cl-2": samples([80.0], [20.0], [40.0], [70.0])}


def test_only_clusters_without_the_latest_window_are_due():
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY,
                       properties={"cl-1": {dc.WINDOW_END_KEY: "2026-10-12 00:00 UTC", dc.WINDOW_HOURS_KEY: "24"},
                                   "cl-2": {dc.WINDOW_END_KEY: "2026-10-11 00:00 UTC", dc.WINDOW_HOURS_KEY: "24"}})
    results = dc.read_daily_cluster_check(api, "ai-1", "00:00", NOW)
    assert list(results) == ["domain-c2"]
    assert results["domain-c2"].window_end == "2026-10-12 00:00 UTC"
    # The clusters of this vCenter only.
    assert api.resource_queries[0]["adapterInstanceId"] == ["ai-1"]


def test_nothing_due_reads_no_history():
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY,
                       properties={"cl-1": {dc.WINDOW_END_KEY: "2026-10-12 00:00 UTC", dc.WINDOW_HOURS_KEY: "24"},
                                   "cl-2": {dc.WINDOW_END_KEY: "2026-10-12 00:00 UTC", dc.WINDOW_HOURS_KEY: "24"}})
    assert dc.read_daily_cluster_check(api, "ai-1", "00:00", NOW) == {}
    assert "api/resources/stats/query" not in api.paths


def test_a_changed_time_makes_every_cluster_due_again():
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY,
                       properties={"cl-1": {dc.WINDOW_END_KEY: "2026-10-12 00:00 UTC", dc.WINDOW_HOURS_KEY: "24"},
                                   "cl-2": {dc.WINDOW_END_KEY: "2026-10-12 00:00 UTC", dc.WINDOW_HOURS_KEY: "24"}})
    assert set(dc.read_daily_cluster_check(api, "ai-1", "06:00", NOW)) == {"domain-c1", "domain-c2"}


def test_at_most_max_clusters_per_cycle(monkeypatch):
    monkeypatch.setattr(dc, "MAX_CLUSTERS_PER_CYCLE", 1)
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY)
    assert list(dc.read_daily_cluster_check(api, "ai-1", "00:00", NOW)) == ["domain-c1"]


def test_failed_history_request_leaves_the_clusters_due():
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY, status_code=500)
    assert dc.read_daily_cluster_check(api, "ai-1", "00:00", NOW) == {}


def test_publish():
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY)
    results = dc.read_daily_cluster_check(api, "ai-1", "00:00", NOW)
    cluster = FakeObject("cluster-b")
    dc.publish(cluster, results["domain-c2"])
    group = f"vCommunity|{dc.GROUP}"
    assert cluster.properties == {
        f"{group}|95th Percentile Cluster Risk": 80.0,
        f"{group}|95th Percentile Cluster Performance": 20.0,
        f"{group}|99th Percentile Capacity Utilization": 70.0,
        f"{group}|Close for Business": 1,
        f"{group}|Window Hours": 24,
        f"{group}|Window End": "2026-10-12 00:00 UTC",
    }


def test_not_due_publishes_nothing():
    cluster = FakeObject("cluster-a")
    dc.publish(cluster, None)
    assert cluster.properties == {}


def test_the_24_hours_end_at_the_set_time():
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY)
    sent = []
    original = api.post
    api.post = lambda path, json: (sent.append(json), original(path, json))[1]
    dc.read_daily_cluster_check(api, "ai-1", "06:00", NOW)
    history = [request for request in sent if "begin" in request][0]
    end = int(datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc).timestamp() * 1000)
    assert history["end"] == end
    assert history["begin"] == end - 24 * 3600 * 1000
    assert history["intervalQuantifier"] == 5


# --- Period --------------------------------------------------------------------------------------------------

def test_parse_period():
    assert dc.parse_period("6") == 6
    assert dc.parse_period(None) == 24
    assert dc.parse_period("") == 24
    assert dc.parse_period("5") == 24          # not in the list: the default


def test_window_ends_every_period_from_the_set_time():
    # 09:30 now. Set time 00:00, every 6 hours: ends at 00:00, 06:00, 12:00, 18:00. Latest: 06:00.
    assert dc.latest_window_end(NOW, 0, 0, 6) == datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)
    # Every hour, from 00:15: latest 09:15.
    assert dc.latest_window_end(NOW, 0, 15, 1) == datetime(2026, 10, 12, 9, 15, tzinfo=timezone.utc)
    # Set time 10:00, every 8 hours: ends at 02:00, 10:00, 18:00. Latest: 02:00.
    assert dc.latest_window_end(NOW, 10, 0, 8) == datetime(2026, 10, 12, 2, 0, tzinfo=timezone.utc)
    # 24 hours is unchanged.
    assert dc.latest_window_end(NOW, 12, 0, 24) == datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


def test_the_window_is_as_long_as_the_period():
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY)
    sent = []
    original = api.post
    api.post = lambda path, json: (sent.append(json), original(path, json))[1]
    results = dc.read_daily_cluster_check(api, "ai-1", "00:00", NOW, period_setting="6")
    history = [request for request in sent if "begin" in request][0]
    end = int(datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc).timestamp() * 1000)
    assert history["end"] == end
    assert history["begin"] == end - 6 * 3600 * 1000
    assert results["domain-c2"].window_hours == 6


def test_a_changed_period_with_the_same_end_is_due_again():
    # At 09:30, with 00:00: a 24-hour and a 12-hour window both end at 00:00. The stored window is 24 hours;
    # changing the setting to 12 hours makes every cluster due again.
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY,
                       properties={"cl-1": {dc.WINDOW_END_KEY: "2026-10-12 00:00 UTC", dc.WINDOW_HOURS_KEY: "24"},
                                   "cl-2": {dc.WINDOW_END_KEY: "2026-10-12 00:00 UTC", dc.WINDOW_HOURS_KEY: "24"}})
    assert dc.read_daily_cluster_check(api, "ai-1", "00:00", NOW, period_setting="24") == {}
    assert set(dc.read_daily_cluster_check(api, "ai-1", "00:00", NOW, period_setting="12")) == {"domain-c1", "domain-c2"}


def test_a_window_without_its_length_is_due_again():
    # Stored before Window Hours existed: recalculated once after the upgrade.
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY,
                       properties={"cl-1": {dc.WINDOW_END_KEY: "2026-10-12 00:00 UTC"}})
    assert "domain-c1" in dc.read_daily_cluster_check(api, "ai-1", "00:00", NOW)
