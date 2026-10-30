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


def test_the_libraries_are_published_from_the_read_of_this_cycle():
    result = CollectResult()
    lib.collect_library_data(sample_data(), None, result)
    assert any(o.get_key().object_kind == lib.LIBRARY_KIND for o in result.objects.values())
    assert any(o.get_key().object_kind == lib.ITEM_KIND for o in result.objects.values())


def test_there_is_no_cache_between_cycles():
    """Each collection cycle is a new process, so a module-level cache never survives to the next cycle. The
    libraries are read in every cycle, and nothing is kept in the module."""
    assert not hasattr(lib, "_cache")
    assert not hasattr(lib, "cached_read")


def test_a_failed_library_read_publishes_nothing_and_logs_a_warning(monkeypatch, caplog):
    class FailingReader:
        def __init__(self, *args, **kwargs):
            raise ConnectionError("vCenter down")

    class NoVCenterApi:
        def query_for_resources(self, query):
            return []

    monkeypatch.setattr(lib, "LibraryReader", FailingReader)
    result = CollectResult()
    lib.run_library_collection("vc", 443, "user", "pw", None, None, NoVCenterApi(), "ai", "uuid", result)
    assert len(result.objects) == 0
    assert "Content library collection failed" in caplog.text


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


def test_tls_modes_for_the_rest_connection():
    assert lib.verify_for(tls.ENABLED, None) == (True, None)
    assert lib.verify_for(tls.TRUST_ON_FIRST_USE, None) == (False, None)
    sha256 = "aa" * 32
    assert lib.verify_for(tls.PINNED, sha256) == (False, sha256)
    assert lib.verify_for(tls.PINNED, "AA:" * 31 + "AA") == (False, "aa" * 32)


@pytest.mark.parametrize("thumbprint", ["", None, "aa" * 20, "aa" * 64 + "bb" * 64])
def test_pinned_needs_a_sha256_thumbprint(thumbprint):
    """A missing, SHA-1 or SHA-512 thumbprint is refused before any connection is made. urllib3 pins SHA-256 here."""
    with pytest.raises(tls.TlsConfigError):
        lib.verify_for(tls.PINNED, thumbprint)


def test_pinned_rest_login_sends_nothing_to_a_server_with_another_certificate(tmp_path):
    pytest.importorskip("cryptography")
    from tls_server import TlsServer
    import requests

    with TlsServer(tmp_path) as server:
        reader = lib.LibraryReader("127.0.0.1", "user", "pw", False, server.port, "bb" * 32)
        with pytest.raises(requests.exceptions.SSLError, match=tls.FINGERPRINT_MISMATCH):
            with reader:
                pass
        assert server.requests == []


def test_pinned_rest_login_reaches_a_server_with_the_pinned_certificate(tmp_path):
    pytest.importorskip("cryptography")
    from tls_server import TlsServer, thumbprint
    import requests

    with TlsServer(tmp_path) as server:
        reader = lib.LibraryReader("127.0.0.1", "user", "pw", False, server.port, thumbprint(server.der))
        # The test server answers the login with HTTP 500, so the login is refused. What matters is that the
        # login request arrived: the certificate matched during the handshake.
        with pytest.raises(requests.HTTPError):
            with reader:
                pass
        assert [method for method, _, _ in server.requests] == ["POST"]
