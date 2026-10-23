#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Trust on First Use of the vCenter certificate: what is recorded, what is reported, and that it never stops.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from properties.vcenter import certificate as cert
from fakes import FakeObject, FakeSuiteApi

OLD = "aa" * 32
NEW = "bb" * 32
NOW = datetime(2026, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
VC_ID = "vc-resource-1"


# ---- the comparison -----------------------------------------------------------------------------------------

def test_first_collection_records_the_certificate():
    assert cert.compare(None, None, NEW, NOW) == cert.CertificateCheck(cert.RECORDED, NEW)


def test_the_same_certificate_is_unchanged():
    assert cert.compare(NEW, None, NEW, NOW) == cert.CertificateCheck(cert.UNCHANGED, NEW)


def test_a_different_certificate_is_changed_and_keeps_the_old_one():
    check = cert.compare(OLD, None, NEW, NOW)
    assert check.status == cert.CHANGED
    assert check.thumbprint == NEW                  # from now on, the new one is compared
    assert check.previous_thumbprint == OLD
    assert check.last_changed == "2026-10-23 12:00:00 UTC"


def test_changed_is_shown_for_24_hours_then_unchanged():
    changed = "2026-10-23 12:00:00 UTC"
    assert cert.compare(NEW, changed, NEW, NOW + timedelta(hours=23)).status == cert.CHANGED
    assert cert.compare(NEW, changed, NEW, NOW + timedelta(hours=24)).status == cert.UNCHANGED


def test_the_reminder_does_not_republish_the_previous_thumbprint():
    """Previous thumbprint and Last Changed are published once, at the change, so they keep that change."""
    check = cert.compare(NEW, "2026-10-23 12:00:00 UTC", NEW, NOW + timedelta(hours=1))
    assert check.previous_thumbprint is None and check.last_changed is None


def test_an_unreadable_certificate_is_unknown_and_keeps_the_recorded_one():
    assert cert.compare(OLD, None, None, NOW) == cert.CertificateCheck(cert.UNKNOWN, None)


def test_an_unreadable_last_changed_is_ignored():
    assert cert.compare(NEW, "not a time", NEW, NOW).status == cert.UNCHANGED


# ---- reading back from VCF Operations and publishing on the vCenter object ----------------------------------

def suite_api(properties=None):
    return FakeSuiteApi(resources={"VMwareAdapter Instance": [(VC_ID, "vcenter", "vc")]},
                        properties={VC_ID: properties or {}})


def test_first_collection_publishes_the_thumbprint_and_status():
    vcenter = FakeObject("vcenter")
    cert.check_and_publish(suite_api(), "ai-1", vcenter, "vc.example.com", NEW, NOW)
    assert vcenter.properties == {cert.STATUS_KEY: cert.RECORDED, cert.THUMBPRINT_KEY: NEW}


def test_a_change_is_published_and_logged_and_does_not_raise(caplog):
    vcenter = FakeObject("vcenter")
    with caplog.at_level(logging.WARNING, logger=cert.logger.name):
        check = cert.check_and_publish(suite_api({cert.THUMBPRINT_KEY: OLD}), "ai-1", vcenter,
                                       "vc.example.com", NEW, NOW)
    assert check.status == cert.CHANGED
    assert vcenter.properties[cert.THUMBPRINT_KEY] == NEW
    assert vcenter.properties[cert.PREVIOUS_THUMBPRINT_KEY] == OLD
    assert vcenter.properties[cert.LAST_CHANGED_KEY] == "2026-10-23 12:00:00 UTC"
    assert "vc.example.com" in caplog.text and OLD in caplog.text and NEW in caplog.text
    assert "Collection continues" in caplog.text


def test_a_suite_api_failure_is_unknown_and_does_not_raise():
    class Broken(FakeSuiteApi):
        def paged_post(self, path, key, json):
            raise ConnectionError("Suite API down")

    vcenter = FakeObject("vcenter")
    check = cert.check_and_publish(Broken(), "ai-1", vcenter, "vc.example.com", NEW, NOW)
    assert check.status == cert.UNKNOWN
    assert vcenter.properties == {cert.STATUS_KEY: cert.UNKNOWN}   # the recorded thumbprint is not overwritten
