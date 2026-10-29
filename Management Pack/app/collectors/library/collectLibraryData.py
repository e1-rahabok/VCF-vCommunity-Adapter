#  Copyright 2026 VCF Operations vCommunity Management Pack

"""Content libraries and their items, read from vCenter through the vSphere Automation REST API.

The objects are Content Library (one per library) and Library Item (one per item, of every type). The design and
its decisions are in docs/development-guide/template-and-library-design.md. The read makes one REST call per item,
so it runs at most once an hour; the last values are kept between reads.
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional

import requests
from aria.ops.object import Identifier, Key, Object
from aria.ops.result import CollectResult
import constants.main
from constants.main import ADAPTER_KIND
from utils import tls

logger = logging.getLogger(__name__)

LIBRARY_KIND = "Content Library"
ITEM_KIND = "Library Item"
LIBRARY_ID_KEY = "Library ID"
ITEM_ID_KEY = "Item ID"
READ_INTERVAL_SECONDS = 3600
GIB = 1024 ** 3


class LibraryReader:
    """A read-only vSphere Automation REST session: a login, GET calls, and the logout.

    verify: True checks the certificate against the trust store. False connects whatever the certificate is,
    as the pyVmomi connection does in Trust on First Use mode.
    """

    def __init__(self, host: str, user: str, password: str, verify: bool, port: int = 443) -> None:
        self.base = f"https://{host}:{port}/api"
        self.user = user
        self.password = password
        self.session = requests.Session()
        self.session.verify = verify

    def __enter__(self) -> "LibraryReader":
        response = self.session.post(f"{self.base}/session", auth=(self.user, self.password), timeout=60)
        response.raise_for_status()
        self.session.headers["vmware-api-session-id"] = response.json()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        try:
            self.session.delete(f"{self.base}/session", timeout=60)
        except requests.RequestException:
            pass
        self.session.close()

    def get(self, path: str) -> Any:
        response = self.session.get(f"{self.base}{path}", timeout=60)
        response.raise_for_status()
        return _value(response.json())


def _value(body: Any) -> Any:
    """The vSphere Automation API wraps some answers in a "value" field, and returns others bare."""
    if isinstance(body, dict) and "value" in body:
        return body["value"]
    return body


def read_libraries(reader: LibraryReader) -> Dict[str, Any]:
    """Every library, and every item of each library: {"libraries": [...], "items": {library id: [...]}}."""
    libraries: List[Dict[str, Any]] = []
    items: Dict[str, List[Dict[str, Any]]] = {}
    for library_id in reader.get("/content/library"):
        library = reader.get(f"/content/library/{library_id}")
        libraries.append(library)
        item_ids = reader.get(f"/content/library/item?library_id={library_id}")
        items[library_id] = [reader.get(f"/content/library/item/{item_id}") for item_id in item_ids]
    return {"libraries": libraries, "items": items}


def verify_for(mode: Optional[str], host: str, port: int, thumbprint: Optional[str]) -> bool:
    """The certificate check for the REST connection, in the same mode as the pyVmomi connection.

    Enabled: the trust store is checked. Pinned: the certificate must match the thumbprint, checked before the
    login, and the trust store is not used. Trust on First Use: nothing is checked here, as in pyVmomi, and the
    certificate is watched separately (properties/vcenter/certificate.py).
    """
    resolved = tls.vcenter_mode(mode)
    if resolved == tls.ENABLED:
        return True
    if resolved == tls.PINNED:
        pinned = tls.normalize_thumbprint(thumbprint)
        if tls.presented_thumbprint(host, port) != pinned:
            raise ConnectionError("The vCenter certificate does not match the pinned thumbprint; the libraries were not read.")
    return False


_cache: Dict[str, Any] = {"read_at": None, "data": None}


def cached_read(read: Callable[[], Dict[str, Any]], now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """The libraries, read at most once an hour. A failed read keeps the last values, and returns them.

    Returns None when no read has ever succeeded.
    """
    now = time.time() if now is None else now
    if _cache["data"] is not None and now - _cache["read_at"] < READ_INTERVAL_SECONDS:
        return _cache["data"]
    try:
        data = read()
    except Exception as exc:
        logger.warning(f"Content library read failed, keeping the last values - {repr(exc)}")
        return _cache["data"]
    _cache["read_at"] = now
    _cache["data"] = data
    return data


def _gib(value: Any) -> float:
    return round(float(value or 0) / GIB, 2)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def publish_libraries(data: Dict[str, Any], vcenter_obj: Optional[Object], result: CollectResult) -> None:
    """Adds the Content Library objects, and their Library Item objects, to the result.

    vcenter_obj: the vCenter object of this vCenter, the parent of each library. None when it is not found.
    """
    for library in data["libraries"]:
        library_obj = Object(Key(ADAPTER_KIND, LIBRARY_KIND, library["name"], [Identifier(LIBRARY_ID_KEY, library["id"])]))
        items = data["items"].get(library["id"], [])
        subscription = library.get("subscription_info") or {}
        library_obj.with_property(f"vCommunity|{LIBRARY_KIND}|Type", _text(library.get("type")))
        library_obj.with_property(f"vCommunity|{LIBRARY_KIND}|Subscription URL", _text(subscription.get("subscription_url")))
        library_obj.with_property(f"vCommunity|{LIBRARY_KIND}|Automatic Sync", _text(subscription.get("automatic_sync_enabled")))
        library_obj.with_property(f"vCommunity|{LIBRARY_KIND}|State", _text((library.get("state_info") or {}).get("state")))
        library_obj.with_metric(f"vCommunity|{LIBRARY_KIND}|Items", len(items))
        library_obj.with_metric(f"vCommunity|{LIBRARY_KIND}|Items Not Stored Locally", sum(1 for item in items if not item.get("cached")))
        library_obj.with_metric(f"vCommunity|{LIBRARY_KIND}|Items Not Security Compliant", sum(1 for item in items if not item.get("security_compliance")))
        library_obj.with_metric(f"vCommunity|{LIBRARY_KIND}|Total Size (GB)", _gib(sum(float(item.get("size") or 0) for item in items)))
        if vcenter_obj is not None:
            library_obj.add_parent(vcenter_obj)
        result.add_object(library_obj)

        for item in items:
            publish_item(item, library_obj, result)


def publish_item(item: Dict[str, Any], library_obj: Object, result: CollectResult) -> None:
    item_obj = Object(Key(ADAPTER_KIND, ITEM_KIND, item["name"], [Identifier(ITEM_ID_KEY, item["id"])]))
    verification = item.get("certificate_verification_info") or {}
    item_obj.with_property(f"vCommunity|{ITEM_KIND}|Type", _text(item.get("type")))
    item_obj.with_property(f"vCommunity|{ITEM_KIND}|Description", _text(item.get("description")))
    item_obj.with_property(f"vCommunity|{ITEM_KIND}|Version", _text(item.get("version")))
    item_obj.with_property(f"vCommunity|{ITEM_KIND}|Content Version", _text(item.get("content_version")))
    item_obj.with_property(f"vCommunity|{ITEM_KIND}|Stored Locally", _text(item.get("cached")))
    item_obj.with_property(f"vCommunity|{ITEM_KIND}|Security Compliant", _text(item.get("security_compliance")))
    item_obj.with_property(f"vCommunity|{ITEM_KIND}|Certificate Verification", _text(verification.get("status")))
    item_obj.with_property(f"vCommunity|{ITEM_KIND}|Last Modified", _text(item.get("last_modified_time")))
    item_obj.with_property(f"vCommunity|{ITEM_KIND}|Last Sync", _text(item.get("last_sync_time")))
    item_obj.with_property(f"vCommunity|{ITEM_KIND}|Source Item ID", _text(item.get("source_id")))
    item_obj.with_metric(f"vCommunity|{ITEM_KIND}|Size (GB)", _gib(item.get("size")))
    library_obj.add_child(item_obj)
    result.add_object(item_obj)


def collect_library_data(
    read: Callable[[], Dict[str, Any]],
    vcenter_obj: Optional[Object],
    result: CollectResult,
    now: Optional[float] = None,
) -> None:
    """Publishes the libraries and items from the cached read. Does nothing when no read has succeeded yet."""
    data = cached_read(read, now)
    if data is None:
        return
    publish_libraries(data, vcenter_obj, result)


def find_vcenter_object(suite_api_client: Any, adapter_instance_id: str, vcenter_uuid: str) -> Optional[Object]:
    """The vCenter object of this Adapter Instance, the one matched by its VMEntityVCID (as collectvCenterData does)."""
    vcenters: List[Object] = suite_api_client.query_for_resources(
        {
            "adapterKind": [constants.main.VCENTER_ADAPTER_KIND],
            "resourceKind": ["VMwareAdapter Instance"],
            "adapterInstanceId": [adapter_instance_id],
        }
    )
    return next((vc for vc in vcenters if vc.get_identifier_value("VMEntityVCID") == vcenter_uuid), None)


def run_library_collection(
    host: str,
    port: int,
    user: str,
    password: str,
    mode: Optional[str],
    thumbprint: Optional[str],
    suite_api_client: Any,
    adapter_instance_id: str,
    vcenter_uuid: str,
    result: CollectResult,
) -> None:
    """The library collection of one cycle, for the adapter's thread pool. A failure is logged, never raised,
    so it cannot stop the rest of the collection."""
    try:
        vcenter_obj = find_vcenter_object(suite_api_client, adapter_instance_id, vcenter_uuid)

        def read() -> Dict[str, Any]:
            verify = verify_for(mode, host, port, thumbprint)
            with LibraryReader(host, user, password, verify, port) as reader:
                return read_libraries(reader)

        collect_library_data(read, vcenter_obj, result)
    except Exception as exc:
        logger.warning(f"Content library collection failed - {repr(exc)}")
