#  Copyright 2026 VCF Operations vCommunity Management Pack
"""How the adapter treats the vCenter Server certificate.

Run from the "Management Pack" folder:  python -m pytest tests

The tests against a local HTTPS server need the 'cryptography' and 'pyvmomi' packages, and skip without them.
"""
import logging
import re
import ssl
import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))

from utils import tls

SHA256 = "ab" * 32
SHA512 = "cd" * 64


# ---- the settings -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("value", [
    SHA256,
    SHA256.upper(),
    ":".join(SHA256[i:i + 2] for i in range(0, 64, 2)),
    ":".join(SHA256[i:i + 2] for i in range(0, 64, 2)).upper(),
    " ".join(SHA256[i:i + 2] for i in range(0, 64, 2)),
    f"  {SHA256}\n",
])
def test_thumbprint_forms_all_normalize_the_same(value):
    assert tls.normalize_thumbprint(value) == SHA256


def test_sha512_thumbprint_is_accepted():
    assert tls.normalize_thumbprint(SHA512) == SHA512


@pytest.mark.parametrize("value, reason", [
    (None, "empty"),
    ("", "empty"),
    ("   ", "empty"),
    ("ab" * 20, "SHA-1"),          # 40 hex characters: SHA-1 is refused for a typed-in thumbprint
    ("ab" * 31, "64"),             # too short
    ("zz" * 32, "hexadecimal"),
])
def test_bad_thumbprint_is_refused(value, reason):
    with pytest.raises(tls.TlsConfigError, match=reason):
        tls.normalize_thumbprint(value)


@pytest.mark.parametrize("value, expected", [
    (None, "Trust on First Use"), ("", "Trust on First Use"), ("  ", "Trust on First Use"),
    ("Trust on First Use", "Trust on First Use"), ("trust on first use", "Trust on First Use"),
    ("Enabled", "Enabled"), ("enabled", "Enabled"), ("Pinned", "Pinned"), ("PINNED", "Pinned"),
])
def test_mode_default_is_trust_on_first_use(value, expected):
    """An Adapter Instance without the setting, such as one created before it existed, gets the default."""
    assert tls.vcenter_mode(value) == expected


@pytest.mark.parametrize("value", ["Off", "Disabled", "None"])
def test_unknown_mode_is_refused(value):
    with pytest.raises(tls.TlsConfigError, match="Unknown"):
        tls.vcenter_mode(value)


def test_default_mode_never_refuses_the_connection():
    """The customer secures their certificates. The default must keep the adapter connecting."""
    assert tls.DEFAULT_VCENTER_MODE == tls.TRUST_ON_FIRST_USE
    assert tls.VCENTER_MODES[0] == tls.DEFAULT_VCENTER_MODE


# ---- the arguments for SmartConnect -------------------------------------------------------------------------

def test_enabled_verifies_the_chain_and_the_host_name():
    args = tls.vcenter_connect_args("Enabled", None)
    assert "disableSslCertValidation" not in args and "thumbprint" not in args
    context = args["sslContext"]
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2


def test_enabled_ignores_a_thumbprint():
    assert "thumbprint" not in tls.vcenter_connect_args("Enabled", SHA256)


def test_pinned_passes_the_normalized_thumbprint():
    args = tls.vcenter_connect_args("Pinned", SHA256.upper())
    assert args == {"disableSslCertValidation": True, "thumbprint": SHA256}


@pytest.mark.parametrize("thumbprint", [None, "", "  "])
def test_pinned_without_a_thumbprint_fails_closed(thumbprint):
    with pytest.raises(tls.TlsConfigError, match="no vCenter Thumbprint"):
        tls.vcenter_connect_args("Pinned", thumbprint)


def test_pinned_with_a_bad_thumbprint_fails_closed():
    with pytest.raises(tls.TlsConfigError):
        tls.vcenter_connect_args("Pinned", "ab" * 20)


@pytest.mark.parametrize("thumbprint", [None, "", SHA256])
def test_trust_on_first_use_connects_whatever_the_certificate(thumbprint):
    """A thumbprint typed in by mistake is ignored, not turned into a pin."""
    assert tls.vcenter_connect_args(None, thumbprint) == {"disableSslCertValidation": True}


# ---- the error messages -------------------------------------------------------------------------------------

def test_untrusted_certificate_says_how_to_fix_it():
    exc = ssl.SSLCertVerificationError("certificate verify failed: self-signed certificate")
    message = tls.explain_connect_error(exc, "vc.example.com")
    assert "vc.example.com" in message and "Pinned" in message


def test_thumbprint_mismatch_shows_the_presented_thumbprint():
    class Fault(Exception):
        msg = f"SHA thumbprint mismatch. Expected: `{'aa' * 32}`, actual: `{SHA256}`"

    message = tls.explain_connect_error(Fault(), "vc.example.com")
    assert SHA256 in message and "do not connect" in message


def test_other_errors_are_not_explained_as_certificate_errors():
    assert tls.explain_connect_error(ConnectionRefusedError("refused"), "vc.example.com") is None


def test_the_messages_name_trust_on_first_use_as_the_way_to_keep_connecting():
    exc = ssl.SSLCertVerificationError("certificate verify failed: self-signed certificate")
    assert "Trust on First Use" in tls.explain_connect_error(exc, "vc.example.com")


# ---- nothing in the code turns the check off ----------------------------------------------------------------

def test_no_hardcoded_tls_bypass_in_the_code():
    """No code path may switch TLS validation off outside the two modules that decide it, by setting.

    utils/tls.py returns the SmartConnect arguments as a dictionary, per mode. utils/guest_http.py is the one place
    that passes verify=False: every call in it is pinned, or unchecked by its mode, and test_guest_http.py covers
    both.
    """
    offenders = []
    for path in APP.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        patterns = [r"disableSslCertValidation\s*=\s*True"]
        if path.name != "guest_http.py":
            patterns.append(r"verify\s*=\s*False")
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                offenders.append(f"{path.relative_to(APP)}: {match.group(0)}")
    assert offenders == []


# ---- against a real TLS server ------------------------------------------------------------------------------

@pytest.fixture
def server(tmp_path):
    pytest.importorskip("cryptography")
    pytest.importorskip("pyVmomi")
    from tls_server import TlsServer
    with TlsServer(tmp_path) as running:
        yield running


def _connect(server, mode, thumbprint):
    from pyVim.connect import SmartConnect
    return SmartConnect(host="127.0.0.1", port=server.port, user="svc", pwd="secret-password",
                        **tls.vcenter_connect_args(mode, thumbprint))


def _posts(server):
    return [path for method, path, _ in server.requests if method == "POST"]


def test_pinned_with_the_right_thumbprint_reaches_the_server(server):
    from tls_server import thumbprint
    from pyVmomi import vim
    with pytest.raises(vim.fault.HostConnectFault):  # the fake server is not a vCenter: it answers the call with an error
        _connect(server, "Pinned", thumbprint(server.der, colons=True, upper=True))
    assert _posts(server) == ["/sdk"]


def test_pinned_with_the_wrong_thumbprint_sends_nothing_to_the_server(server):
    """The credentials go in a POST to /sdk. A wrong thumbprint must stop the connection before it."""
    with pytest.raises(Exception) as caught:
        _connect(server, "Pinned", "aa" * 32)
    assert _posts(server) == []
    assert all(b"secret-password" not in body for _, _, body in server.requests)
    assert "thumbprint" in (tls.explain_connect_error(caught.value, "127.0.0.1") or "").lower()


def test_pinned_with_the_thumbprint_of_another_certificate_is_refused(server, tmp_path):
    from tls_server import TlsServer, thumbprint
    other_directory = tmp_path / "other"
    other_directory.mkdir()
    from pyVmomi import vim
    with TlsServer(other_directory) as other:
        with pytest.raises(vim.fault.HostConnectFault):
            _connect(server, "Pinned", thumbprint(other.der))
    assert _posts(server) == []


def test_enabled_refuses_a_self_signed_certificate_before_any_request(server):
    with pytest.raises(ssl.SSLCertVerificationError):
        _connect(server, "Enabled", None)
    assert server.requests == []


def test_trust_on_first_use_connects_to_a_self_signed_certificate(server):
    from pyVmomi import vim
    with pytest.raises(vim.fault.HostConnectFault):  # reaches the fake server, which is not a vCenter
        _connect(server, "Trust on First Use", None)
    assert _posts(server) == ["/sdk"]


# ---- reading the certificate for Trust on First Use ---------------------------------------------------------

def test_presented_thumbprint_is_the_sha256_of_the_certificate(server):
    from tls_server import thumbprint
    assert tls.presented_thumbprint("127.0.0.1", server.port) == thumbprint(server.der, "sha256")


def test_reading_the_certificate_sends_nothing(server):
    """Only the TLS handshake: no request, so no user name or password, reaches the server."""
    tls.presented_thumbprint("127.0.0.1", server.port)
    assert server.requests == []


def test_an_unreadable_certificate_gives_none_and_never_raises(caplog):
    import socket
    with socket.socket() as unused:
        unused.bind(("127.0.0.1", 0))
        closed_port = unused.getsockname()[1]
    with caplog.at_level(logging.WARNING, logger=tls.logger.name):
        assert tls.presented_thumbprint("127.0.0.1", closed_port) is None
    assert "not compared" in caplog.text
