#  Copyright 2026 VCF Operations vCommunity Management Pack
"""How the adapter checks the vCenter Server certificate.

Three modes, set per Adapter Instance. See docs/configuration-guide/tls-and-security.md.

  Enabled   The certificate chain and host name are checked against the trust store of the Cloud Proxy container.
            The default.
  Pinned    The certificate must match a SHA-256 (or SHA-512) thumbprint set on the Adapter Instance. For a
            vCenter with a self-signed or internal CA certificate that the container does not trust.
  Disabled  Nothing is checked. For a lab only: the vCenter credentials can be read by anyone on the path.

A wrong or missing setting fails closed: the connection is refused, never made unchecked.
"""
import logging
import re
import ssl
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

ENABLED = "Enabled"
PINNED = "Pinned"
DISABLED = "Disabled"

VCENTER_MODES = [ENABLED, PINNED, DISABLED]
DEFAULT_VCENTER_MODE = ENABLED

# SHA-256 and SHA-512 only. SHA-1 is not accepted for a thumbprint that a person types in.
_VCENTER_THUMBPRINT_LENGTHS = (64, 128)
_HEX = re.compile(r"^[0-9a-f]+$")


class TlsConfigError(ValueError):
    """The TLS settings of the Adapter Instance cannot be used. The message says what to change."""


def normalize_thumbprint(value: Optional[str], lengths=_VCENTER_THUMBPRINT_LENGTHS) -> str:
    """A thumbprint as lower case hex with no separators. Raises TlsConfigError when it is not a valid one.

    Accepts the usual forms: AA:BB:CC..., aa bb cc..., aabbcc...
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
    """The mode from the Adapter Instance. Empty means the default, Enabled. Anything unknown is refused."""
    mode = (value or "").strip() or DEFAULT_VCENTER_MODE
    for known in VCENTER_MODES:
        if mode.lower() == known.lower():
            return known
    raise TlsConfigError(f"Unknown vCenter TLS validation '{value}'. Use one of: {', '.join(VCENTER_MODES)}.")


def vcenter_connect_args(mode: Optional[str], thumbprint: Optional[str]) -> Dict[str, Any]:
    """The TLS arguments for pyVim.connect.SmartConnect, for the mode and thumbprint of the Adapter Instance."""
    mode = vcenter_mode(mode)

    if mode == ENABLED:
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        return {"sslContext": context}

    if mode == PINNED:
        if not (thumbprint or "").strip():
            raise TlsConfigError(
                "vCenter TLS validation is 'Pinned', but no vCenter Thumbprint is set on the Adapter Instance."
            )
        # pyVmomi compares the certificate of every new connection with the thumbprint, before it sends anything,
        # including the login. The chain is not checked: the thumbprint is the identity.
        return {"disableSslCertValidation": True, "thumbprint": normalize_thumbprint(thumbprint)}

    logger.warning(
        "vCenter TLS validation is Disabled. The vCenter certificate is not checked and the vCenter credentials "
        "can be read by anyone on the network path. Use Enabled or Pinned outside a lab."
    )
    return {"disableSslCertValidation": True}


def explain_connect_error(exc: BaseException, host: str, mode: Optional[str] = None) -> Optional[str]:
    """A message that says what to change, when a vCenter connection failed on the certificate. Otherwise None."""
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
            "it. Otherwise do not connect: something else may be answering as the vCenter."
        )
    if isinstance(exc, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in text:
        return (
            f"The certificate of {host} is not trusted by the Cloud Proxy ({exc}). Either install a certificate "
            f"from a CA that the Cloud Proxy trusts, or set 'vCenter TLS Validation' to {PINNED} and enter the "
            "vCenter Thumbprint."
        )
    return None
