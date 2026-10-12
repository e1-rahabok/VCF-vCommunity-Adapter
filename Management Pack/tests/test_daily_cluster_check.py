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


def test_95th_percentile_ignores_the_highest_5_percent():
    # 288 samples of a day: 1..288. Position ceil(0.95 x 288) = 274.
    assert dc.percentile_95([float(n) for n in range(288, 0, -1)]) == 274.0
    # One spike in a quiet day is ignored.
    assert dc.percentile_95([1.0] * 287 + [50.0]) == 1.0
    assert dc.percentile_95([]) is None


def samples(risk, performance, cpu, memory):
    return {dc.CLUSTER_RISK_SCORE: risk, dc.CLUSTER_PERFORMANCE_SCORE: performance,
            dc.CPU_UTILIZATION: cpu, dc.MEMORY_UTILIZATION: memory}


def test_utilization_is_the_higher_of_cpu_and_memory():
    values = dc.daily_values(samples([90.0], [95.0], [40.0], [70.0]))
    assert values == {dc.RISK: 90.0, dc.PERFORMANCE: 95.0, dc.UTILIZATION: 70.0, dc.RESULT: 0}


def test_result_follows_the_placeholder_rule():
    assert dc.daily_values(samples([30.0], [95.0], [40.0], [40.0]))[dc.RESULT] == 1   # risk too low
    assert dc.daily_values(samples([90.0], [95.0], [85.0], [40.0]))[dc.RESULT] == 1   # utilization too high


def test_no_result_when_an_input_has_no_data():
    values = dc.daily_values({dc.CLUSTER_RISK_SCORE: [90.0], dc.CLUSTER_PERFORMANCE_SCORE: [95.0]})
    assert values == {dc.RISK: 90.0, dc.PERFORMANCE: 95.0, dc.UTILIZATION: None, dc.RESULT: None}


CLUSTERS = {"ClusterComputeResource": [("cl-1", "cluster-a", "domain-c1"), ("cl-2", "cluster-b", "domain-c2")]}
HISTORY = {"cl-1": samples([90.0, 80.0], [95.0], [40.0], [70.0]), "cl-2": samples([20.0], [95.0], [40.0], [70.0])}


def test_only_clusters_without_the_latest_window_are_due():
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY,
                       properties={"cl-1": {dc.WINDOW_END_KEY: "2026-10-12 00:00 UTC"},
                                   "cl-2": {dc.WINDOW_END_KEY: "2026-10-11 00:00 UTC"}})
    results = dc.read_daily_cluster_check(api, "ai-1", "00:00", NOW)
    assert list(results) == ["domain-c2"]
    assert results["domain-c2"].window_end == "2026-10-12 00:00 UTC"
    # The clusters of this vCenter only.
    assert api.resource_queries[0]["adapterInstanceId"] == ["ai-1"]


def test_nothing_due_reads_no_history():
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY,
                       properties={"cl-1": {dc.WINDOW_END_KEY: "2026-10-12 00:00 UTC"},
                                   "cl-2": {dc.WINDOW_END_KEY: "2026-10-12 00:00 UTC"}})
    assert dc.read_daily_cluster_check(api, "ai-1", "00:00", NOW) == {}
    assert "api/resources/stats/query" not in api.paths


def test_a_changed_time_makes_every_cluster_due_again():
    api = FakeSuiteApi(resources=CLUSTERS, samples=HISTORY,
                       properties={"cl-1": {dc.WINDOW_END_KEY: "2026-10-12 00:00 UTC"},
                                   "cl-2": {dc.WINDOW_END_KEY: "2026-10-12 00:00 UTC"}})
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
        f"{group}|95th Percentile Cluster Risk": 20.0,
        f"{group}|95th Percentile Cluster Performance": 95.0,
        f"{group}|95th Percentile Cluster Utilization": 70.0,
        f"{group}|Result": 1,
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
