#  Copyright 2026 VCF Operations vCommunity Management Pack
"""The HTTPS calls of the GuestAPI file transfers, with the ESXi host certificate checked.

InitiateFileTransferToGuest and InitiateFileTransferFromGuest return a URL on the ESXi host that runs the VM.
The adapter sends or reads the guest script and its output there. An ESXi certificate is usually signed by a CA
that the Cloud Proxy does not trust, so the chain cannot be checked. Instead the certificate is pinned: its
thumbprint must equal the one that vCenter records for that host (host.summary.config.sslThumbprint). vCenter is
already authenticated by the vCenter TLS settings, so the thumbprint comes over a trusted path, with no setup.

  Pinned    The default. The connection is refused when the certificate does not match, or when vCenter has no
            thumbprint for the host.
  Disabled  The legacy behaviour: nothing is checked. Set per Adapter Instance, for a lab only.

See docs/configuration-guide/tls-and-security.md.
"""
import logging
import re
import threading
import warnings
from typing import Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.exceptions import InsecureRequestWarning

logger = logging.getLogger(__name__)

PINNED = "Pinned"
DISABLED = "Disabled"
GUEST_MODES = [PINNED, DISABLED]
DEFAULT_GUEST_MODE = PINNED

# vCenter reports the ESXi thumbprint as SHA-1. urllib3 takes SHA-1 (40 hex characters) and SHA-256 (64).
_ACCEPTED_LENGTHS = (40, 64)
_TIMEOUT = (10, 300)

_mode = DEFAULT_GUEST_MODE
_host_thumbprints: Dict[str, Optional[str]] = {}
_lock = threading.Lock()


class GuestTlsError(RuntimeError):
    """The certificate of the ESXi host cannot be checked. The transfer is not made."""


def configure(mode: Optional[str]) -> str:
    """Set the mode for this collection. Empty means the default, Pinned. Anything unknown is refused."""
    global _mode
    value = (mode or "").strip() or DEFAULT_GUEST_MODE
    for known in GUEST_MODES:
        if value.lower() == known.lower():
            _mode = known
            _host_thumbprints.clear()
            if known == DISABLED:
                logger.warning(
                    "Guest file transfer TLS validation is Disabled. The ESXi certificate is not checked. "
                    "Use Pinned outside a lab."
                )
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
    """The SSL thumbprint of the ESXi host that runs the VM, as vCenter records it. Cached per host."""
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


class _PinnedAdapter(HTTPAdapter):
    """Accepts only a server certificate with this fingerprint. urllib3 compares it during the TLS handshake,
    before any request is sent, and it replaces the chain check."""

    def __init__(self, fingerprint: str, **kwargs):
        self._fingerprint = fingerprint
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["assert_fingerprint"] = self._fingerprint
        super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)


def _session(vm) -> requests.Session:
    """A new session for one transfer. Never shared, so a setting cannot carry over to another host."""
    session = requests.Session()
    if _mode == PINNED:
        session.mount("https://", _PinnedAdapter(host_thumbprint(vm)))
    return session


def put(vm, url: str, data) -> requests.Response:
    """PUT to a file transfer URL of the host that runs vm. Raises GuestTlsError when the host is not trusted."""
    with _session(vm) as session:
        return _send(session, "PUT", url, data=data)


def get(vm, url: str) -> requests.Response:
    """GET from a file transfer URL of the host that runs vm. Raises GuestTlsError when the host is not trusted."""
    with _session(vm) as session:
        return _send(session, "GET", url)


def _send(session: requests.Session, method: str, url: str, **kwargs) -> requests.Response:
    # verify=False is passed on every call, in both modes. In Pinned mode the adapter has a fingerprint, and urllib3
    # checks that instead of the chain. It has to be the argument of the call: a REQUESTS_CA_BUNDLE variable
    # overrides the setting of the session, which would bring the chain check back and refuse every ESXi host.
    try:
        with warnings.catch_warnings():
            if _mode == DISABLED:
                warnings.simplefilter("ignore", InsecureRequestWarning)
            return session.request(method, url, timeout=_TIMEOUT, verify=False, **kwargs)
    except requests.exceptions.SSLError as exc:
        if _mode == PINNED and "ingerprint" in str(exc):
            raise GuestTlsError(
                "The certificate of the ESXi host does not match the thumbprint that vCenter records for it, "
                f"so nothing was sent: {exc}"
            ) from exc
        raise GuestTlsError(f"TLS error talking to the ESXi host, so nothing was sent: {exc}") from exc
