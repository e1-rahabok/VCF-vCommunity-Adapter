#  Copyright 2026 VCF Operations vCommunity Management Pack
"""The collection result uses PER_OBJECT relationship updates.

With the default (AUTO) the platform removes every Business Application link the pack does not return, as soon as the
result has one library or template relationship. PER_OBJECT only replaces the links of objects the pack returns.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import adapter
from aria.ops.result import RelationshipUpdateModes


def test_collect_result_uses_per_object_relationship_updates(monkeypatch):
    monkeypatch.setattr(adapter, "_collect_cycle", lambda adapter_instance, result, warnings: None)
    monkeypatch.setattr(adapter.collection_health, "start", lambda: None)
    monkeypatch.setattr(adapter.collection_health, "stop", lambda warnings: None)
    monkeypatch.setattr(adapter, "timingSummary", lambda: None)

    result = adapter.collect(None)

    assert result.update_relationships == RelationshipUpdateModes.PER_OBJECT
