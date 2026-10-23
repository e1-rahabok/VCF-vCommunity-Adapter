#  Copyright 2026 VCF Operations vCommunity Management Pack
"""How the adapter treats the vCenter Server certificate.

For a VMware administrator
--------------------------
The adapter logs in to vCenter with the service account of the Adapter Instance. The vCenter certificate is what
proves that the server answering is really that vCenter. Many vCenters in the field use the certificate signed by
the vCenter's own VMCA, or a self-signed one, which the Cloud Proxy does not trust. Securing that is the customer's
choice, so by default the adapter never refuses to connect because of the certificate. It watches it instead.

The setting "vCenter TLS Validation" on the Adapter Instance (Advanced Settings) has three modes:

  Trust on First Use  The default. The adapter connects whatever the certificate, the same way the VCF Operations
                      vCenter account accepts a certificate when it is first added. Every collection it reads the
                      certificate's SHA-256 thumbprint and compares it with the one it recorded on the vCenter
                      object in VCF Operations:
                        - none recorded yet: it records this one (status "Recorded").
                        - the same: nothing to report (status "Unchanged").
                        - a different one: it writes a warning to the adapter log, keeps the old thumbprint and the
                          time of the change as properties, and from then on watches the new one (status
                          "Changed", shown for 24 hours). Collection goes on.
                      A changed certificate is normal after a planned certificate replacement. When nobody
                      replaced it, something else may be answering as the vCenter: compare it with vCenter.
                      The comparison is done in properties/vcenter/certificate.py.
  Enabled             Opt-in. The certificate chain and the host name must be trusted by the Cloud Proxy, or the
                      adapter does not connect. For a vCenter with a certificate from a CA that the Cloud Proxy
                      trusts.
  Pinned              Opt-in. The certificate must match the "vCenter Thumbprint (SHA-256)" set on the Adapter
                      Instance, or the adapter does not connect. The comparison happens before the user name and
                      password are sent. For a self-signed or internal CA certificate, when the customer wants
                      the connection refused rather than reported.

Enabled and Pinned refuse the connection when the check fails. That is their purpose, and the customer chooses
them. An unknown mode, or Pinned without a valid thumbprint, is refused too: a setting the customer typed wrong is
never quietly treated as "no check".

The overall approach, for the documentation: docs/configuration-guide/tls-and-security.md.
"""
import hashlib
import logging
import re
import socket
import ssl
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

TRUST_ON_FIRST_USE = "Trust on First Use"
ENABLED = "Enabled"
PINNED = "Pinned"

# The default first: VCF Operations shows the drop-down in this order.
VCENTER_MODES = [TRUST_ON_FIRST_USE, ENABLED, PINNED]
DEFAULT_VCENTER_MODE = TRUST_ON_FIRST_USE

# SHA-256 and SHA-512 only. SHA-1 is not accepted for a thumbprint that a person types in.
_VCENTER_THUMBPRINT_LENGTHS = (64, 128)
_HEX = re.compile(r"^[0-9a-f]+$")

# Reading the certificate is one TLS handshake. It must not hold up the collection when vCenter is slow.
_HANDSHAKE_TIMEOUT_SECONDS = 10


class TlsConfigError(ValueError):
    """The TLS settings of the Adapter Instance cannot be used. The message says what to change."""


def normalize_thumbprint(value: Optional[str], lengths=_VCENTER_THUMBPRINT_LENGTHS) -> str:
    """A thumbprint as lower case hex with no separators. Raises TlsConfigError when it is not a valid one.

    Accepts the forms an administrator copies from OpenSSL, a browser or vCenter: AA:BB:CC..., aa bb cc..., aabbcc...
    """
    cleaned = re.sub(r"[\s:\-]", "", (value or "")).lower()
    if not cleaned:
        raise TlsConfigError("The vCenter thumbprint is empty.")
    if not _HEX.match(cleaned):
        raise TlsConfigError("The vCenter thumbprint must be hexadecimal, with or without ':' between the bytes.")
    if len(cleaned) not in lengths:
        raise TlsConfigError(
            "The vCenter thumbprint must be a SHA-256 (64 hex characters) or SHA-512 (128) value, "
            f"not {len(cleaned)} characters. SHA-1 is not accepted."
        )
    return cleaned


def vcenter_mode(value: Optional[str]) -> str:
    """The mode from the Adapter Instance. Empty means the default, Trust on First Use. Anything unknown is refused.

    Empty is the normal case for an Adapter Instance created before this setting existed: it gets the default, so
    it keeps connecting exactly as before.
    """
    mode = (value or "").strip() or DEFAULT_VCENTER_MODE
    for known in VCENTER_MODES:
        if mode.lower() == known.lower():
            return known
    raise TlsConfigError(f"Unknown vCenter TLS validation '{value}'. Use one of: {', '.join(VCENTER_MODES)}.")


def vcenter_connect_args(mode: Optional[str], thumbprint: Optional[str]) -> Dict[str, Any]:
    """The TLS arguments for pyVim.connect.SmartConnect, for the mode and thumbprint of the Adapter Instance."""
    mode = vcenter_mode(mode)

    if mode == ENABLED:
        # The Cloud Proxy's trust store decides. Host name checked too. TLS 1.2 or later, as vCenter 7 and 8 require.
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        return {"sslContext": context}

    if mode == PINNED:
        if not (thumbprint or "").strip():
            raise TlsConfigError(
                "vCenter TLS validation is 'Pinned', but no vCenter Thumbprint is set on the Adapter Instance."
            )
        # pyVmomi compares the certificate of every new connection with the thumbprint before it sends anything,
        # the login included. The chain is not checked: the thumbprint is the identity.
        return {"disableSslCertValidation": True, "thumbprint": normalize_thumbprint(thumbprint)}

    # Trust on First Use: connect whatever the certificate. It is watched after the login, by presented_thumbprint()
    # and properties/vcenter/certificate.py, and a change is reported, never refused.
    return {"disableSslCertValidation": True}


def presented_thumbprint(host: str, port: int = 443) -> Optional[str]:
    """The SHA-256 thumbprint of the certificate that vCenter presents now, as lower case hex. None when unreadable.

    One TLS handshake, with no check, only to read the certificate. Nothing is sent: no user name, no password, no
    request. The value is the same one OpenSSL prints with `openssl x509 -noout -fingerprint -sha256`, without the
    colons. Any error is logged and gives None, so reading the certificate can never stop a collection.
    """
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((host, int(port)), timeout=_HANDSHAKE_TIMEOUT_SECONDS) as raw:
            with context.wrap_socket(raw, server_hostname=host) as tls_socket:
                der = tls_socket.getpeercert(binary_form=True)
    except (OSError, ValueError) as exc:
        logger.warning(f"Could not read the certificate of vCenter {host}:{port}, so it is not compared: {exc}")
        return None
    if not der:
        logger.warning(f"vCenter {host}:{port} presented no certificate, so it is not compared.")
        return None
    return hashlib.sha256(der).hexdigest()


def explain_connect_error(exc: BaseException, host: str, mode: Optional[str] = None) -> Optional[str]:
    """A message that says what to change, when a vCenter connection failed on the certificate. Otherwise None.

    Only Enabled and Pinned can fail on the certificate, because Trust on First Use does not check it before the
    login. The message is what an administrator sees in Validate Connection and in the adapter log.
    """
    # pyVmomi wraps a thumbprint mismatch in a HostConnectFault. The reason is in its msg and in the exception it
    # was raised from.
    chain = [exc, getattr(exc, "msg", None), exc.__cause__, exc.__context__]
    text = " | ".join(f"{type(part).__name__}: {part}" for part in chain if part is not None)
    if "ThumbprintMismatchException" in text or "thumbprint mismatch" in text.lower():
        actual = re.search(r"actual: `([0-9a-fA-F]+)`", text)
        shown = f" The certificate it presented has the thumbprint {actual.group(1)}." if actual else ""
        return (
            f"The certificate of {host} does not match the vCenter Thumbprint on the Adapter Instance.{shown} "
            "If the certificate was replaced on purpose, compare that thumbprint with the one in vCenter, then set "
            "it. Otherwise do not connect: something else may be answering as the vCenter. To report a changed "
            f"certificate instead of refusing it, set 'vCenter TLS Validation' to {TRUST_ON_FIRST_USE}."
        )
    if isinstance(exc, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in text:
        return (
            f"The certificate of {host} is not trusted by the Cloud Proxy ({exc}). Either install a certificate "
            f"from a CA that the Cloud Proxy trusts, set 'vCenter TLS Validation' to {PINNED} and enter the "
            f"vCenter Thumbprint, or set it to {TRUST_ON_FIRST_USE}, which connects and reports a changed "
            "certificate."
        )
    return None
