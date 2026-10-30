#  Copyright 2026 VCF Operations vCommunity Management Pack

"""Content libraries and their items, read from vCenter through the vSphere Automation REST API.

The objects are Content Library (one per library) and Library Item (one per item, of every type). The design and
its decisions are in docs/development-guide/template-and-library-design.md. The read makes one REST call per item,
and it runs in every collection cycle. Each cycle is a new process, so nothing is kept from one cycle to the next.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import requests
from aria.ops.object import Identifier, Key, Object
from aria.ops.result import CollectResult
from constants.main import ADAPTER_KIND
from utils import tls

logger = logging.getLogger(__name__)

LIBRARY_KIND = "Content Library"
ITEM_KIND = "Library Item"
LIBRARY_ID_KEY = "Library ID"
ITEM_ID_KEY = "Item ID"
GIB = 1024 ** 3


class LibraryReader:
    """A read-only vSphere Automation REST session: a login, GET calls, and the logout.

    verify: True checks the certificate against the trust store. False connects whatever the certificate is,
    as the pyVmomi connection does in Trust on First Use mode.
    fingerprint: when set, the server certificate must have this SHA-256 fingerprint. It is checked during the TLS
    handshake, before the login, as in Pinned mode for pyVmomi.
    """

    def __init__(
        self, host: str, user: str, password: str, verify: bool, port: int = 443, fingerprint: Optional[str] = None
    ) -> None:
        self.base = f"https://{host}:{port}/api"
        self.user = user
        self.password = password
        self.session = requests.Session()
        self.session.verify = verify
        if fingerprint:
            self.session.mount("https://", tls.PinnedAdapter(fingerprint))

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


def verify_for(mode: Optional[str], thumbprint: Optional[str]) -> Tuple[bool, Optional[str]]:
    """The certificate check for the REST connection, in the same mode as the pyVmomi connection.

    Returns (verify, fingerprint), for LibraryReader.
    Enabled: the trust store is checked. Pinned: the certificate must match the SHA-256 thumbprint, during the TLS
    handshake, and the trust store is not used. Trust on First Use: nothing is checked here, as in pyVmomi, and the
    certificate is watched separately (properties/vcenter/certificate.py).
    """
    resolved = tls.vcenter_mode(mode)
    if resolved == tls.ENABLED:
        return True, None
    if resolved == tls.PINNED:
        pinned = tls.normalize_thumbprint(thumbprint)
        if len(pinned) != 64:
            raise tls.TlsConfigError(
                "The REST connection to vCenter needs a SHA-256 vCenter Thumbprint (64 hex characters) in Pinned mode."
            )
        return False, pinned
    return False, None


def _gib(value: Any) -> float:
    return round(float(value or 0) / GIB, 2)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def publish_libraries(data: Dict[str, Any], result: CollectResult) -> None:
    """Adds the Content Library objects, and their Library Item objects, to the result."""
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


def collect_library_data(data: Dict[str, Any], result: CollectResult) -> None:
    """Publishes the libraries and items read in this cycle."""
    publish_libraries(data, result)


def run_library_collection(
    host: str,
    port: int,
    user: str,
    password: str,
    mode: Optional[str],
    thumbprint: Optional[str],
    result: CollectResult,
) -> None:
    """The library collection of one cycle, for the adapter's thread pool. A failure is logged, never raised,
    so it cannot stop the rest of the collection."""
    try:
        verify, fingerprint = verify_for(mode, thumbprint)
        with LibraryReader(host, user, password, verify, port, fingerprint) as reader:
            data = read_libraries(reader)
        collect_library_data(data, result)
    except Exception as exc:
        if tls.FINGERPRINT_MISMATCH in str(exc):
            logger.warning("The vCenter certificate does not match the pinned thumbprint; the libraries were not read.")
        else:
            logger.warning(f"Content library collection failed - {repr(exc)}")
