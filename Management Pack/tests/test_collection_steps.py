#  Copyright 2026 VCF Operations vCommunity Management Pack
"""The collection steps that the review changed: a failed vCenter read is not an empty one, a bad VM does not stop
the VM loop, a failed configuration read does not discard the cycle, and the TLS warnings are visible.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import inspect
import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import pytest
from aria.ops.result import CollectResult
import adapter
from collectors.vm import collectVMData
from definition import get_adapter_definition
from utils import config_files
from utils import tls
from utils import vi_property_collector


# ---- a failed vCenter read is not an empty one (BUG-10) ------------------------------------------------------


class FailingViewManager:
    def CreateContainerView(self, *args):
        raise RuntimeError("vCenter session expired")


class FakeView:
    def __init__(self):
        self.destroyed = False

    def Destroy(self):
        self.destroyed = True


class FailingCollector:
    def __init__(self, view):
        self.view = view

    def RetrievePropertiesEx(self, *args):
        raise RuntimeError("the page request failed")


def test_a_failed_property_read_raises_instead_of_returning_no_objects():
    content = SimpleNamespace(rootFolder=None, viewManager=FailingViewManager(), propertyCollector=None)
    with pytest.raises(RuntimeError, match="session expired"):
        vi_property_collector.retrieve_properties(content, object, ["name"])


def test_the_container_view_is_released_when_the_read_fails_part_way(monkeypatch):
    from pyVmomi import vim
    view = FakeView()
    content = SimpleNamespace(
        rootFolder=None,
        viewManager=SimpleNamespace(CreateContainerView=lambda *args: view),
        propertyCollector=FailingCollector(view),
    )
    # pyVmomi only accepts managed objects in an ObjectSpec, and the fake view is not one. The spec types are not
    # what this test is about, so they are replaced for its length.
    monkeypatch.setattr(vi_property_collector.vmodl.query.PropertyCollector, "ObjectSpec", lambda **kw: SimpleNamespace(**kw))
    monkeypatch.setattr(vi_property_collector.vmodl.query.PropertyCollector, "FilterSpec", lambda **kw: SimpleNamespace(**kw))
    with pytest.raises(RuntimeError, match="page request failed"):
        vi_property_collector.retrieve_properties(content, vim.HostSystem, ["name"])
    assert view.destroyed is True


# ---- a bad VM does not stop the VM loop (BUG-07) -------------------------------------------------------------


class BadVm:
    """A VM object whose reference cannot be read. Before the fix, the handler then failed with a NameError."""

    @property
    def obj(self):
        raise ValueError("no object reference")


class NoVCenterObjects:
    def query_for_resources(self, query):
        return []


def test_a_vm_that_fails_before_its_name_is_read_is_skipped_and_named_unknown(monkeypatch, caplog):
    monkeypatch.setattr(collectVMData, "retrieve_properties", lambda *args: [BadVm()])
    monkeypatch.setattr(collectVMData, "read_vms", lambda *args: [])
    monkeypatch.setattr(collectVMData, "read_vm_performance_stats", lambda *args: {})
    monkeypatch.setattr(collectVMData, "read_vm_shares", lambda *args: {})
    guest = collectVMData.GuestSettings("Disabled", "Disabled", "u", "p", "")

    collectVMData.collect_vm_data(NoVCenterObjects(), "ai", CollectResult(), SimpleNamespace(), guest, [], [])

    assert "Skipping VM data collection on Unknown" in caplog.text


# ---- a failed configuration read does not discard the cycle (BUG-11) ----------------------------------------


class ErroringSuiteApi:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url):
        raise ConnectionError("connection reset by peer")


class FakeAdapterInstance:
    def __init__(self, suite_api):
        self.suite_api_client = suite_api

    def get_identifier_value(self, name, default=None):
        return "events-list"


def test_an_event_list_that_cannot_be_read_gives_an_empty_list_and_a_problem():
    problems = []
    text = adapter._read_event_log_config(FakeAdapterInstance(ErroringSuiteApi()), problems)
    assert text == ""
    assert "could not be read from VCF Operations" in problems[0]
    assert "connection reset by peer" in problems[0]


def test_a_configuration_file_that_cannot_be_read_gives_an_empty_list_and_a_problem():
    problems = []
    assert adapter.get_config_file_data(FakeAdapterInstance(ErroringSuiteApi()), "services", problems) == []
    assert len(problems) == 1


def test_the_unreadable_problem_names_the_file_and_the_reason():
    text = config_files.unreadable_problem("services", "timeout")
    assert "'services.xml'" in text and "timeout" in text


# ---- the TLS warnings are visible (SEC-01) -------------------------------------------------------------------


def test_trust_on_first_use_says_in_the_log_what_it_does(caplog):
    caplog.set_level(logging.INFO)
    tls.vcenter_connect_args(tls.TRUST_ON_FIRST_USE, None)
    assert "Trust on First Use: the certificate of vCenter is not checked" in caplog.text


def test_the_setting_description_warns_about_trust_on_first_use():
    definition = json.dumps(get_adapter_definition().to_json())
    assert "WARNING: it sends the user name and password before the certificate is checked" in definition


def test_trust_on_first_use_is_logged_as_information_so_the_default_does_not_fire_the_alert(caplog):
    """The Collection Warnings alert counts warnings. The default setting must not raise one on every cycle."""
    tls.vcenter_connect_args(None, None)
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING and "Trust on First Use" in r.getMessage()]
    assert warnings == []


# ---- the unused parameter is gone (BUG-13) -------------------------------------------------------------------


def test_explain_connect_error_takes_no_unused_mode():
    assert list(inspect.signature(tls.explain_connect_error).parameters) == ["exc", "host"]


# ---- the guest steps of the VM loop: which VMs get them, and when the budget stops them ----------------------


class OneVmSuiteApi:
    def query_for_resources(self, query):
        return [SimpleNamespace(get_identifier_value=lambda key: "vm-1")]


class FakeResult:
    def __init__(self):
        self.objects = []

    def add_object(self, obj):
        self.objects.append(obj)


def run_one_windows_vm(monkeypatch, guest, budget_has_time=True):
    calls = []
    vm_ref = SimpleNamespace(_moId="vm-1")
    vm_data = SimpleNamespace(obj=vm_ref, propSet=[SimpleNamespace(name="name", val="win-01")])
    monkeypatch.setattr(collectVMData, "retrieve_properties", lambda *args: [vm_data])
    monkeypatch.setattr(collectVMData, "read_vms", lambda *args: [])
    monkeypatch.setattr(collectVMData, "read_vm_performance_stats", lambda *args: {})
    monkeypatch.setattr(collectVMData, "read_vm_shares", lambda *args: {})
    for name in ("collect_vm_disk", "collect_vm_configurations"):
        monkeypatch.setattr(collectVMData, name, lambda *args, **kwargs: None)
    for name in ("collect_vm_service_properties", "collect_vm_os_information_properties", "collect_windows_events"):
        monkeypatch.setattr(collectVMData, name, lambda *args, _name=name: calls.append(_name))

    class Budget:
        def __init__(self, *args, **kwargs):
            pass

        def has_time(self):
            return budget_has_time

    monkeypatch.setattr(collectVMData, "GuestBudget", Budget)
    result = FakeResult()
    collectVMData.collect_vm_data(OneVmSuiteApi(), "ai", result, SimpleNamespace(), guest, [], [])
    return calls, result


def test_a_windows_vm_gets_the_guest_steps_that_are_enabled(monkeypatch):
    guest = collectVMData.GuestSettings("Enabled", "Enabled", "u", "p", "<Events/>", ["Spooler"])
    calls, result = run_one_windows_vm(monkeypatch, guest)
    assert calls == ["collect_vm_service_properties", "collect_vm_os_information_properties", "collect_windows_events"]
    assert len(result.objects) == 1


def test_the_event_steps_wait_for_a_readable_event_list(monkeypatch):
    guest = collectVMData.GuestSettings("Disabled", "Enabled", "u", "p", "")
    calls, _ = run_one_windows_vm(monkeypatch, guest)
    assert calls == []


def test_no_guest_step_runs_once_the_budget_is_spent(monkeypatch):
    guest = collectVMData.GuestSettings("Enabled", "Enabled", "u", "p", "<Events/>", ["Spooler"])
    calls, result = run_one_windows_vm(monkeypatch, guest, budget_has_time=False)
    assert calls == []
    assert len(result.objects) == 1
