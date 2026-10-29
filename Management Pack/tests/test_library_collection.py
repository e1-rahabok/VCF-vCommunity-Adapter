#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Content Library and Library Item: the read, its cache, the objects, and their parents.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import pytest
from aria.ops.object import Key, Object
from aria.ops.result import CollectResult
from collectors.library import collectLibraryData as lib
from utils import tls

GIB = 1024 ** 3


def sample_data():
    libraries = [
        {
            "id": "lib-1",
            "name": "cl-vks01",
            "type": "SUBSCRIBED",
            "subscription_info": {"subscription_url": "https://example.test/lib.json", "automatic_sync_enabled": True},
            "state_info": {"state": "ACTIVE"},
        },
    ]
    items = {
        "lib-1": [
            {"id": "item-1", "name": "ubuntu", "type": "ovf", "size": 2 * GIB, "cached": True,
             "security_compliance": True, "certificate_verification_info": {"status": "SUCCEEDED"}},
            {"id": "item-2", "name": "tools", "type": "other", "size": GIB, "cached": False,
             "security_compliance": False},
        ]
    }
    return {"libraries": libraries, "items": items}


def vcenter_object():
    return Object(Key("VMWARE", "VMwareAdapter Instance", "vc", []))


def test_objects_have_parents_and_children():
    result = CollectResult()
    vc = vcenter_object()
    lib.publish_libraries(sample_data(), vc, result)

    library = next(o for o in result.objects.values() if o.get_key().object_kind == "Content Library")
    items = [o for o in result.objects.values() if o.get_key().object_kind == "Library Item"]
    assert len(items) == 2
    assert library.get_parents() == {vc.get_key()}
    assert {item.get_key() for item in items} == library.get_children()
    for item in items:
        assert item.get_parents() == {library.get_key()}


def test_library_metrics_count_its_items():
    result = CollectResult()
    lib.publish_libraries(sample_data(), None, result)
    library = next(o for o in result.objects.values() if o.get_key().object_kind == "Content Library")
    assert library.get_last_metric_value(f"vCommunity|{lib.LIBRARY_KIND}|Items") == 2
    assert library.get_last_metric_value(f"vCommunity|{lib.LIBRARY_KIND}|Items Not Stored Locally") == 1
    assert library.get_last_metric_value(f"vCommunity|{lib.LIBRARY_KIND}|Items Not Security Compliant") == 1
    assert library.get_last_metric_value(f"vCommunity|{lib.LIBRARY_KIND}|Total Size (GB)") == 3.0


def test_library_properties_show_the_subscription():
    result = CollectResult()
    lib.publish_libraries(sample_data(), None, result)
    library = next(o for o in result.objects.values() if o.get_key().object_kind == "Content Library")
    assert library.get_last_property_value(f"vCommunity|{lib.LIBRARY_KIND}|Type") == "SUBSCRIBED"
    assert library.get_last_property_value(f"vCommunity|{lib.LIBRARY_KIND}|Subscription URL") == "https://example.test/lib.json"
    assert library.get_last_property_value(f"vCommunity|{lib.LIBRARY_KIND}|Automatic Sync") == "True"


def test_item_properties_and_size():
    result = CollectResult()
    lib.publish_libraries(sample_data(), None, result)
    item = next(o for o in result.objects.values() if o.get_key().name == "ubuntu")
    assert item.get_last_property_value(f"vCommunity|{lib.ITEM_KIND}|Certificate Verification") == "SUCCEEDED"
    assert item.get_last_property_value(f"vCommunity|{lib.ITEM_KIND}|Stored Locally") == "True"
    assert item.get_last_metric_value(f"vCommunity|{lib.ITEM_KIND}|Size (GB)") == 2.0


def test_cache_reads_at_most_once_an_hour_and_keeps_the_last_values():
    calls = []

    def read():
        calls.append(1)
        return {"libraries": [], "items": {}, "n": len(calls)}

    lib._cache.update(read_at=None, data=None)
    first = lib.cached_read(read, now=1000.0)
    again = lib.cached_read(read, now=1000.0 + lib.READ_INTERVAL_SECONDS - 1)
    assert first is again and len(calls) == 1

    def failing():
        raise ConnectionError("vCenter down")

    kept = lib.cached_read(failing, now=1000.0 + lib.READ_INTERVAL_SECONDS + 1)
    assert kept is first
    assert len(calls) == 1


def test_no_read_yet_publishes_nothing():
    lib._cache.update(read_at=None, data=None)

    def failing():
        raise ConnectionError("vCenter down")

    result = CollectResult()
    lib.collect_library_data(failing, None, result, now=5000.0)
    assert len(result.objects) == 0


def test_read_follows_the_items_of_each_library():
    class FakeReader:
        def __init__(self):
            self.paths = []

        def get(self, path):
            self.paths.append(path)
            if path == "/content/library":
                return ["lib-1"]
            if path == "/content/library/lib-1":
                return {"id": "lib-1", "name": "cl-vks01"}
            if path.startswith("/content/library/item?library_id="):
                return ["item-1"]
            if path == "/content/library/item/item-1":
                return {"id": "item-1", "name": "ubuntu", "size": 1}
            raise AssertionError(path)

    reader = FakeReader()
    data = lib.read_libraries(reader)
    assert data["libraries"] == [{"id": "lib-1", "name": "cl-vks01"}]
    assert data["items"] == {"lib-1": [{"id": "item-1", "name": "ubuntu", "size": 1}]}
    assert len(reader.paths) == 4


def test_tls_modes_for_the_rest_connection(monkeypatch):
    assert lib.verify_for(tls.ENABLED, "vc", 443, None) is True
    assert lib.verify_for(tls.TRUST_ON_FIRST_USE, "vc", 443, None) is False

    pinned = "AA:" * 31 + "AA"
    monkeypatch.setattr(tls, "presented_thumbprint", lambda host, port: "bb" * 32)
    with pytest.raises(ConnectionError):
        lib.verify_for(tls.PINNED, "vc", 443, pinned)

    monkeypatch.setattr(tls, "presented_thumbprint", lambda host, port: "aa" * 32)
    assert lib.verify_for(tls.PINNED, "vc", 443, pinned) is False
