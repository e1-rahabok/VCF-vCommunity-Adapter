#  Copyright 2026 VCF Operations vCommunity Management Pack
"""The HTTPS calls of the GuestAPI file transfers, with the ESXi host certificate checked.

For a VMware administrator
--------------------------
Windows Service and Windows Event Log monitoring run a small PowerShell script inside the VM through VMware Tools
(the vSphere GuestAPI). The script and its output do not travel through vCenter: vCenter returns a URL on the ESXi
host that runs the VM (InitiateFileTransferToGuest and InitiateFileTransferFromGuest), and the adapter uploads or
downloads the file there over HTTPS.

An ESXi certificate is usually signed by the VMCA of its vCenter, which the Cloud Proxy does not trust, so the
certificate chain cannot be checked. But vCenter already knows each host's certificate: it records its thumbprint
when the host is added or reconnected (host.summary.config.sslThumbprint in the vSphere API). The adapter pins the
transfer to that thumbprint. It needs no setup.

The setting "Guest File Transfer TLS Validation" on the Adapter Instance (Advanced Settings) has three modes:

  Pinned    The default. The host must present the certificate that vCenter recorded for it. When vCenter has no
            thumbprint for the host, or the host of the VM cannot be found, the transfer goes ahead without the
            check, and the adapter log says so once per host and collection. So monitoring never stops because
            the environment lacks something.
  Strict    Opt-in. As Pinned, but when there is no thumbprint to compare with, the transfer is refused and the VM
            is skipped.
  Disabled  Opt-in. The certificate is not checked at all.

In Pinned and Strict, a host that presents a DIFFERENT certificate than the one vCenter recorded is refused, and
the VM is skipped. That is not a sign of an insecure environment, which Pinned tolerates: it means the server
answering is not the host vCenter knows. The certificate is compared during the TLS handshake, before the script or
its output is sent. The VM is skipped for that collection, and the reason is in the adapter log.

The overall approach, for the documentation: docs/configuration-guide/tls-and-security.md.
"""
import logging
import re
import threading
import warnings
from typing import Dict, Optional, Set

import requests
from urllib3.exceptions import InsecureRequestWarning
from utils import tls

logger = logging.getLogger(__name__)

PINNED = "Pinned"
STRICT = "Strict"
DISABLED = "Disabled"
# The default first: VCF Operations shows the drop-down in this order.
GUEST_MODES = [PINNED, STRICT, DISABLED]
DEFAULT_GUEST_MODE = PINNED

# vCenter reports the ESXi thumbprint as SHA-1. urllib3 takes SHA-1 (40 hex characters) and SHA-256 (64).
_ACCEPTED_LENGTHS = (40, 64)
# 10 seconds to connect to the host, 300 to read: a slow VM must not hold the collection for ever.
_TIMEOUT = (10, 300)

_mode = DEFAULT_GUEST_MODE
_host_thumbprints: Dict[str, Optional[str]] = {}   # host MoRef id -> thumbprint, or None when vCenter has none
_hosts_warned: Set[str] = set()                    # hosts already named in the log as transferred unchecked
_lock = threading.Lock()


class GuestTlsError(RuntimeError):
    """The certificate of the ESXi host cannot be checked, or does not match. The transfer is not made."""


def configure(mode: Optional[str]) -> str:
    """Set the mode for this collection. Empty means the default, Pinned. Anything unknown is refused.

    Called once at the start of every collection. It also forgets the thumbprints of the last collection, so a
    replaced ESXi certificate is picked up from vCenter at the next collection.
    """
    global _mode
    value = (mode or "").strip() or DEFAULT_GUEST_MODE
    for known in GUEST_MODES:
        if value.lower() == known.lower():
            with _lock:
                _mode = known
                _host_thumbprints.clear()
                _hosts_warned.clear()
            if known == DISABLED:
                logger.info("Guest file transfer TLS validation is Disabled: the ESXi certificate is not checked.")
            return known
    raise GuestTlsError(f"Unknown guest TLS validation '{mode}'. Use one of: {', '.join(GUEST_MODES)}.")


def current_mode() -> str:
    return _mode


def normalize(thumbprint: Optional[str]) -> str:
    cleaned = re.sub(r"[\s:\-]", "", thumbprint or "").lower()
    if len(cleaned) not in _ACCEPTED_LENGTHS or not re.fullmatch(r"[0-9a-f]+", cleaned):
        raise GuestTlsError("vCenter returned no valid SSL thumbprint for the ESXi host.")
    return cleaned


def host_thumbprint(vm) -> str:
    """The SSL thumbprint of the ESXi host that runs the VM, as vCenter records it. Cached per host.

    Raises GuestTlsError when the host cannot be found, or vCenter has no valid thumbprint for it.
    """
    try:
        host = vm.runtime.host
        key = host._moId
    except Exception as exc:
        raise GuestTlsError(f"Cannot find the ESXi host of {getattr(vm, 'name', 'the VM')}: {exc}") from exc

    with _lock:
        if key in _host_thumbprints:
            cached = _host_thumbprints[key]
            if cached is None:
                raise GuestTlsError(f"vCenter has no SSL thumbprint for ESXi host {key}.")
            return cached
    try:
        value = normalize(host.summary.config.sslThumbprint)
    except GuestTlsError:
        value = None
    except Exception as exc:
        raise GuestTlsError(f"Cannot read the SSL thumbprint of ESXi host {key}: {exc}") from exc
    with _lock:
        _host_thumbprints[key] = value
    if value is None:
        raise GuestTlsError(f"vCenter has no SSL thumbprint for ESXi host {key}.")
    return value


def _pin_for(vm) -> Optional[str]:
    """The thumbprint to pin the transfer to, or None to transfer without the check.

    Disabled: always None. Strict: the thumbprint, or GuestTlsError when there is none. Pinned: the thumbprint, or
    None with one warning per host when there is none.
    """
    if _mode == DISABLED:
        return None
    try:
        return host_thumbprint(vm)
    except GuestTlsError as reason:
        if _mode == STRICT:
            raise
        host_key = _host_key(vm)
        with _lock:
            first_time = host_key not in _hosts_warned
            _hosts_warned.add(host_key)
        if first_time:
            logger.warning(
                f"{reason} Guest file transfers to this host go ahead without checking its certificate. "
                f"Set 'Guest File Transfer TLS Validation' to {STRICT} to skip such VMs instead."
            )
        return None


def _host_key(vm) -> str:
    try:
        return vm.runtime.host._moId
    except Exception:
        return f"host of {getattr(vm, 'name', 'a VM')}"


def _session(vm):
    """(a new session for one transfer, whether it is pinned). Never shared, so a pin cannot carry over to another
    host."""
    session = requests.Session()
    fingerprint = _pin_for(vm)
    if fingerprint:
        session.mount("https://", tls.PinnedAdapter(fingerprint))
    return session, bool(fingerprint)


def put(vm, url: str, data) -> requests.Response:
    """PUT to a file transfer URL of the host that runs vm. Raises GuestTlsError when the host is refused."""
    session, pinned = _session(vm)
    with session:
        return _send(session, pinned, "PUT", url, data=data)


def get(vm, url: str) -> requests.Response:
    """GET from a file transfer URL of the host that runs vm. Raises GuestTlsError when the host is refused."""
    session, pinned = _session(vm)
    with session:
        return _send(session, pinned, "GET", url)


def _send(session: requests.Session, pinned: bool, method: str, url: str, **kwargs) -> requests.Response:
    # verify=False is passed on every call. When pinned, the adapter has a fingerprint, and urllib3 checks that
    # instead of the chain. It has to be the argument of the call: a REQUESTS_CA_BUNDLE variable overrides the
    # setting of the session, which would bring the chain check back and refuse every ESXi host.
    try:
        with warnings.catch_warnings():
            if not pinned:
                # Unchecked on purpose (Disabled, or Pinned without a thumbprint): already logged, no warning per call.
                warnings.simplefilter("ignore", InsecureRequestWarning)
            return session.request(method, url, timeout=_TIMEOUT, verify=False, **kwargs)
    except requests.exceptions.SSLError as exc:
        if pinned and tls.FINGERPRINT_MISMATCH in str(exc):
            raise GuestTlsError(
                "The certificate of the ESXi host does not match the thumbprint that vCenter records for it, "
                f"so nothing was sent: {exc}"
            ) from exc
        raise GuestTlsError(f"TLS error talking to the ESXi host, so nothing was sent: {exc}") from exc
