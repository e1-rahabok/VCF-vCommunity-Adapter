#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Tier probe: one probe metric on every Tier object, and no metric when the query fails.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from aria.ops.object import Key, Object
from aria.ops.result import CollectResult
from metrics.container import tier_probe


class FakeSuiteApiClient:
    def __init__(self, tiers=None, error=None):
        self.tiers = tiers or []
        self.error = error
        self.queries = []

    def query_for_resources(self, query):
        self.queries.append(query)
        if self.error:
            raise self.error
        return self.tiers


def tier(name):
    return Object(Key("Container", "Tier", name, None))


def test_every_tier_gets_the_probe_metric():
    client = FakeSuiteApiClient(tiers=[tier("biz-a"), tier("biz-b")])
    result = CollectResult()
    tier_probe.collect_tier_probe(client, result)
    assert client.queries == [{"adapterKind": ["Container"], "resourceKind": ["Tier"]}]
    assert len(result.objects) == 2
    for obj in result.objects.values():
        assert obj.get_metric_values(tier_probe.PROBE_KEY) == [tier_probe.PROBE_VALUE]


def test_no_tiers_publishes_nothing():
    result = CollectResult()
    tier_probe.collect_tier_probe(FakeSuiteApiClient(), result)
    assert len(result.objects) == 0


def test_a_failed_query_does_not_raise():
    result = CollectResult()
    tier_probe.collect_tier_probe(FakeSuiteApiClient(error=RuntimeError("down")), result)
    assert len(result.objects) == 0
