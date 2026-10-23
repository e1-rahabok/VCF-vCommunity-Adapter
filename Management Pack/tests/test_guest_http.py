#  Copyright 2026 VCF Operations vCommunity Management Pack
"""The HTTPS calls of the GuestAPI file transfers: the ESXi host certificate is pinned to what vCenter records.

Run from the "Management Pack" folder:  python -m pytest tests

Needs the 'cryptography' package for the local HTTPS server, and skips without it.
"""
import logging
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from utils import guest_http


class FakeHostSummaryConfig:
    def __init__(self, ssl_thumbprint, reads):
        self._ssl_thumbprint = ssl_thumbprint
        self._reads = reads

    @property
    def sslThumbprint(self):
        self._reads.append(1)
        return self._ssl_thumbprint


class FakeHost:
    def __init__(self, ssl_thumbprint, moid="host-10"):
        self._moId = moid
        self.reads = []

        class Summary:
            pass

        self.summary = Summary()
        self.summary.config = FakeHostSummaryConfig(ssl_thumbprint, self.reads)


class FakeVm:
    def __init__(self, host, name="vm-1"):
        self.name = name

        class Runtime:
            pass

        self.runtime = Runtime()
        self.runtime.host = host


@pytest.fixture(autouse=True)
def default_mode():
    guest_http.configure(None)
    yield
    guest_http.configure(None)


@pytest.fixture
def server(tmp_path):
    pytest.importorskip("cryptography")
    from tls_server import TlsServer
    with TlsServer(tmp_path) as running:
        yield running


def url(server, path="/guestFile?id=1"):
    return f"https://127.0.0.1:{server.port}{path}"


def vcenter_thumbprint(server, **kwargs):
    """The thumbprint as vCenter reports it for an ESXi host: SHA-1, upper case, with colons."""
    from tls_server import thumbprint
    return thumbprint(server.der, "sha1", colons=True, upper=True, **kwargs)


# ---- the settings -------------------------------------------------------------------------------------------

def test_default_mode_is_pinned():
    assert guest_http.DEFAULT_GUEST_MODE == guest_http.PINNED
    assert guest_http.configure(None) == guest_http.PINNED
    assert guest_http.configure("") == guest_http.PINNED
    assert guest_http.current_mode() == guest_http.PINNED


def test_mode_is_not_case_sensitive():
    assert guest_http.configure("disabled") == guest_http.DISABLED
    assert guest_http.configure("strict") == guest_http.STRICT
    assert guest_http.configure("pinned") == guest_http.PINNED


def test_unknown_mode_is_refused_not_treated_as_off():
    with pytest.raises(guest_http.GuestTlsError, match="Unknown"):
        guest_http.configure("Off")
    assert guest_http.current_mode() == guest_http.PINNED


def test_disabled_says_so_in_the_log(caplog):
    with caplog.at_level(logging.INFO, logger=guest_http.logger.name):
        guest_http.configure("Disabled")
    assert "Disabled" in caplog.text and "not checked" in caplog.text


@pytest.mark.parametrize("value", [None, "", "not-hex", "ab" * 10, "ab" * 33])
def test_a_thumbprint_vcenter_does_not_have_is_refused(value):
    with pytest.raises(guest_http.GuestTlsError):
        guest_http.normalize(value)


@pytest.mark.parametrize("value", ["ab" * 20, ("ab:" * 20).rstrip(":").upper(), "ab" * 32])
def test_sha1_and_sha256_thumbprints_are_accepted(value):
    assert guest_http.normalize(value) == value.replace(":", "").lower()


# ---- pinned: the certificate is the one vCenter records -----------------------------------------------------

def test_put_with_the_recorded_thumbprint(server):
    vm = FakeVm(FakeHost(vcenter_thumbprint(server)))
    response = guest_http.put(vm, url(server), b"script body")
    assert response.status_code == 200
    assert server.requests == [("PUT", "/guestFile?id=1", b"script body")]


def test_get_with_the_recorded_thumbprint(server):
    vm = FakeVm(FakeHost(vcenter_thumbprint(server)))
    response = guest_http.get(vm, url(server))
    assert response.status_code == 200 and response.text == "script output"


def test_a_ca_bundle_in_the_environment_does_not_bring_back_the_chain_check(server, monkeypatch):
    """requests lets REQUESTS_CA_BUNDLE override the setting of a session. A Cloud Proxy may set it."""
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(server.cert_file.parent / "no-such-bundle.pem"))
    monkeypatch.setenv("CURL_CA_BUNDLE", str(server.cert_file.parent / "no-such-bundle.pem"))
    vm = FakeVm(FakeHost(vcenter_thumbprint(server)))
    assert guest_http.put(vm, url(server), b"x").status_code == 200


def test_pinned_transfer_raises_no_insecure_request_warning(server):
    vm = FakeVm(FakeHost(vcenter_thumbprint(server)))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert guest_http.put(vm, url(server), b"x").status_code == 200


def test_a_sha256_thumbprint_pins_too(server):
    from tls_server import thumbprint
    vm = FakeVm(FakeHost(thumbprint(server.der, "sha256", colons=True)))
    assert guest_http.put(vm, url(server), b"x").status_code == 200


def test_the_wrong_thumbprint_sends_nothing(server):
    vm = FakeVm(FakeHost("AA:" * 19 + "AA"))
    with pytest.raises(guest_http.GuestTlsError, match="does not match the thumbprint"):
        guest_http.put(vm, url(server), b"the script, and anything in it")
    assert server.requests == []


def test_the_wrong_thumbprint_reads_nothing(server):
    vm = FakeVm(FakeHost("AA:" * 19 + "AA"))
    with pytest.raises(guest_http.GuestTlsError, match="does not match the thumbprint"):
        guest_http.get(vm, url(server))
    assert server.requests == []


# ---- no thumbprint in vCenter: Pinned goes ahead and says so, Strict refuses ----------------------------------

@pytest.mark.parametrize("recorded", [None, "", "garbage"])
def test_pinned_without_a_recorded_thumbprint_transfers_and_warns_once(server, recorded, caplog):
    """The environment lacks a thumbprint: monitoring must not stop because of it."""
    host = FakeHost(recorded)
    with caplog.at_level(logging.WARNING, logger=guest_http.logger.name):
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # one log line per host, not an InsecureRequestWarning per call
            assert guest_http.put(FakeVm(host, "vm-1"), url(server), b"x").status_code == 200
            assert guest_http.get(FakeVm(host, "vm-2"), url(server)).status_code == 200
    warnings_logged = [r for r in caplog.records if "without checking its certificate" in r.getMessage()]
    assert len(warnings_logged) == 1
    assert "Strict" in warnings_logged[0].getMessage()


def test_pinned_with_a_vm_without_a_host_transfers(server):
    assert guest_http.put(FakeVm(host=None), url(server), b"x").status_code == 200


@pytest.mark.parametrize("recorded", [None, "", "garbage"])
def test_strict_without_a_recorded_thumbprint_fails_closed_without_connecting(server, recorded):
    guest_http.configure("Strict")
    vm = FakeVm(FakeHost(recorded))
    with pytest.raises(guest_http.GuestTlsError, match="no .*thumbprint"):
        guest_http.put(vm, url(server), b"x")
    assert server.requests == []


def test_strict_with_a_vm_without_a_host_fails_closed(server):
    guest_http.configure("Strict")
    with pytest.raises(guest_http.GuestTlsError, match="Cannot find the ESXi host"):
        guest_http.put(FakeVm(host=None), url(server), b"x")
    assert server.requests == []


def test_strict_with_the_recorded_thumbprint_transfers(server):
    guest_http.configure("Strict")
    assert guest_http.put(FakeVm(FakeHost(vcenter_thumbprint(server))), url(server), b"x").status_code == 200


def test_a_wrong_thumbprint_is_refused_in_strict_too(server):
    guest_http.configure("Strict")
    with pytest.raises(guest_http.GuestTlsError, match="does not match the thumbprint"):
        guest_http.put(FakeVm(FakeHost("AA:" * 19 + "AA")), url(server), b"x")
    assert server.requests == []


def test_pinning_does_not_leak_to_the_next_transfer(server):
    """A good host, then a wrong one: the second is refused, so no session keeps an earlier decision."""
    good = FakeVm(FakeHost(vcenter_thumbprint(server), moid="host-1"))
    wrong = FakeVm(FakeHost("AA:" * 19 + "AA", moid="host-2"))
    assert guest_http.put(good, url(server), b"x").status_code == 200
    with pytest.raises(guest_http.GuestTlsError, match="does not match the thumbprint"):
        guest_http.put(wrong, url(server), b"y")
    assert [body for _, _, body in server.requests] == [b"x"]


def test_the_thumbprint_of_a_host_is_read_from_vcenter_once(server):
    host = FakeHost(vcenter_thumbprint(server))
    first, second = FakeVm(host, "vm-1"), FakeVm(host, "vm-2")
    guest_http.put(first, url(server), b"a")
    guest_http.get(second, url(server))
    guest_http.put(first, url(server), b"b")
    assert len(host.reads) == 1


def test_configure_forgets_the_thumbprints_of_the_last_collection(server):
    host = FakeHost(vcenter_thumbprint(server))
    guest_http.put(FakeVm(host), url(server), b"a")
    guest_http.configure(None)
    guest_http.put(FakeVm(host), url(server), b"b")
    assert len(host.reads) == 2


# ---- disabled: nothing checked, on request ------------------------------------------------------------------

def test_disabled_transfers_without_checking_the_certificate(server):
    guest_http.configure("Disabled")
    vm = FakeVm(FakeHost(None))  # no thumbprint needed: nothing is checked
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # no InsecureRequestWarning in the log of every transfer
        assert guest_http.put(vm, url(server), b"x").status_code == 200
        assert guest_http.get(vm, url(server)).status_code == 200
