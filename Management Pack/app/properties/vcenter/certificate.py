#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Trust on First Use: watch the vCenter certificate, and report when it changes.

For a VMware administrator
--------------------------
This is the default of "vCenter TLS Validation" (see utils/tls.py). The adapter does not refuse a vCenter because
of its certificate. Instead, every collection it compares the certificate vCenter presents with the one it saw
before, and publishes the result on the vCenter object in VCF Operations, under vCommunity|Certificate:

  SHA-256 Thumbprint           The thumbprint of the certificate vCenter presents now. The same value as
                               `openssl x509 -noout -fingerprint -sha256`, in lower case and without colons.
  Status                       Recorded   The first collection: this thumbprint is now the one to compare with.
                               Unchanged  The same certificate as the last collection.
                               Changed    A different certificate within the last 24 hours. Alert on this.
                               Unknown    The certificate could not be read this collection. Nothing was compared.
  Previous SHA-256 Thumbprint  The thumbprint before the last change. Published only when a change is seen.
  Last Changed                 When the last change was seen, in UTC. Published only when a change is seen.

Where the previous thumbprint is kept: in VCF Operations itself, as the SHA-256 Thumbprint property of the vCenter
object. Each collection reads it back through the Suite API. So it survives a restart of the Cloud Proxy and an
upgrade of the pack, and nothing is stored in the adapter container.

What "Changed" means: after a planned certificate replacement, it is expected, and it clears after 24 hours.
When nobody replaced the certificate, another server may be answering as the vCenter, and it has received the
service account password: compare the new thumbprint with the certificate in vCenter, and change the password if
they differ. The collection itself goes on in both cases.

Limits, by design:
  - The check is made after the login, so it reports a change. It does not prevent one. To refuse the connection
    instead, set "vCenter TLS Validation" to Enabled or Pinned.
  - The very first certificate is trusted as it is: there is nothing to compare it with.
  - If the Suite API answers with an error when the recorded thumbprint is read, this collection is treated as
    the first one, and the thumbprint it sees is recorded.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import NamedTuple, Optional

from constants.main import VCENTER_ADAPTER_KIND
from utils.ops_stats import query_resources, read_latest_properties

logger = logging.getLogger(__name__)

THUMBPRINT_KEY = "vCommunity|Certificate|SHA-256 Thumbprint"
STATUS_KEY = "vCommunity|Certificate|Status"
PREVIOUS_THUMBPRINT_KEY = "vCommunity|Certificate|Previous SHA-256 Thumbprint"
LAST_CHANGED_KEY = "vCommunity|Certificate|Last Changed"

RECORDED = "Recorded"
UNCHANGED = "Unchanged"
CHANGED = "Changed"
UNKNOWN = "Unknown"

# How long Status stays "Changed" after a change: long enough for an alert or a daily report to see it.
CHANGED_SHOWN_FOR = timedelta(hours=24)
_TIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"


class CertificateCheck(NamedTuple):
    """The outcome of one comparison. None means: do not publish that property this collection."""
    status: str
    thumbprint: Optional[str]
    previous_thumbprint: Optional[str] = None
    last_changed: Optional[str] = None


def compare(recorded: Optional[str], last_changed: Optional[str], presented: Optional[str],
            now: datetime) -> CertificateCheck:
    """Compares the certificate vCenter presents now with the one recorded before. No I/O, so it is easy to test.

    recorded      the SHA-256 Thumbprint property read back from VCF Operations, or None the first time
    last_changed  the Last Changed property read back, or None when no change was ever seen
    presented     the thumbprint read from vCenter this collection, or None when it could not be read
    """
    if not presented:
        # Nothing to compare. The recorded thumbprint is left as it is, so the next collection compares with it.
        return CertificateCheck(UNKNOWN, None)

    if not recorded:
        return CertificateCheck(RECORDED, presented)

    if presented != recorded:
        return CertificateCheck(CHANGED, presented, previous_thumbprint=recorded,
                                last_changed=now.strftime(_TIME_FORMAT))

    changed_at = _parse_time(last_changed)
    if changed_at is not None and now - changed_at < CHANGED_SHOWN_FOR:
        return CertificateCheck(CHANGED, presented)
    return CertificateCheck(UNCHANGED, presented)


def check_and_publish(suite_api_client, adapter_instance_id: str, vcenter_obj, vcenter_host: str,
                      presented: Optional[str], now: Optional[datetime] = None) -> CertificateCheck:
    """Reads the recorded thumbprint, compares, and publishes the properties on the vCenter object.

    Never raises: watching the certificate must not stop the collection of everything else.
    """
    now = now or datetime.now(timezone.utc)
    try:
        recorded, last_changed = _read_recorded(suite_api_client, adapter_instance_id)
    except Exception as exc:
        logger.warning(f"Could not read the recorded vCenter certificate, so it is not compared this time: {exc!r}")
        recorded, last_changed, presented = None, None, None

    check = compare(recorded, last_changed, presented, now)

    vcenter_obj.with_property(STATUS_KEY, check.status)
    if check.thumbprint:
        vcenter_obj.with_property(THUMBPRINT_KEY, check.thumbprint)
    if check.previous_thumbprint:
        vcenter_obj.with_property(PREVIOUS_THUMBPRINT_KEY, check.previous_thumbprint)
        vcenter_obj.with_property(LAST_CHANGED_KEY, check.last_changed)
        logger.warning(
            f"The certificate of vCenter {vcenter_host} has changed: SHA-256 thumbprint {check.previous_thumbprint} "
            f"before, {check.thumbprint} now. Collection continues. If nobody replaced the certificate, compare "
            "the new thumbprint with the certificate in vCenter."
        )
    elif check.status == RECORDED:
        logger.info(f"Recorded the certificate of vCenter {vcenter_host}: SHA-256 thumbprint {check.thumbprint}.")
    return check


def _read_recorded(suite_api_client, adapter_instance_id: str):
    """(SHA-256 Thumbprint, Last Changed) as last published on the vCenter object, each None when absent."""
    vcenters = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "VMwareAdapter Instance", adapter_instance_id)
    if not vcenters:
        return None, None
    # One vCenter adapter instance holds one vCenter object.
    properties = read_latest_properties(suite_api_client, [vcenters[0].id], [THUMBPRINT_KEY, LAST_CHANGED_KEY])
    values = properties.get(vcenters[0].id, {})
    return values.get(THUMBPRINT_KEY), values.get(LAST_CHANGED_KEY)


def _parse_time(text: Optional[str]) -> Optional[datetime]:
    try:
        return datetime.strptime(text, _TIME_FORMAT).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None
