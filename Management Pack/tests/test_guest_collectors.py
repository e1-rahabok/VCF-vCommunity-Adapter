#  Copyright 2026 VCF Operations vCommunity Management Pack
"""The Windows guest collectors (services, OS information, event logs) and their shared steps, with fakes for the
GuestAPI. No VM is needed.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import pytest
from aria.ops.event import Criticality
from events.vm import collect_windows_event_logs as events
from properties.vm import vmOSInformation as os_info
from properties.vm import vmService as services
from utils import guest_ops


# ---- fakes ---------------------------------------------------------------------------------------------------


class Clock:
    """A clock that only moves when the code sleeps, so the timeout path runs at once."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeProcessManager:
    def __init__(self, exit_code=None):
        self.exit_code = exit_code
        self.terminated = []

    def StartProgram(self, vm, creds, spec):
        return 42

    def ListProcessesInGuest(self, vm, creds, pids):
        return [SimpleNamespace(exitCode=self.exit_code)]

    def TerminateProcess(self, vm, creds, pid):
        self.terminated.append(pid)


class FakeFileManager:
    def __init__(self, temp_dir="C:\\Windows\\Temp\\run-1"):
        self.temp_dir = temp_dir
        self.deleted = []

    def CreateTemporaryDirectory(self, vm, creds, prefix, suffix, path):
        return self.temp_dir

    def DeleteDirectoryInGuest(self, vm, creds, path, recursive):
        self.deleted.append(path)

    def InitiateFileTransferFromGuest(self, vm, creds, path):
        return SimpleNamespace(url="https://esxi.example/guestFile")


class FakeContent:
    def __init__(self, file_manager=None, process_manager=None):
        self.guestOperationsManager = SimpleNamespace(
            fileManager=file_manager or FakeFileManager(),
            processManager=process_manager or FakeProcessManager(exit_code=0),
        )


class FakeVm:
    def __init__(self, name="win-01", tools="toolsOk", family="windowsGuest"):
        self.name = name
        self.guest = SimpleNamespace(toolsStatus=tools, guestFamily=family)


class FakeVmObject:
    """Collects what a collector publishes on the VM object."""

    def __init__(self):
        self.properties = {}
        self.events = []

    def with_property(self, key, value):
        self.properties[key] = value

    def with_event(self, **kwargs):
        self.events.append(kwargs)


class FakeResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


SERVICE_CSV = (
    '"Name","DisplayName","Status","StartType"\n'
    '"Spooler","Print Spooler","Running","Automatic"\n'
    '"ClickToRunSvc","Microsoft Office Click-to-Run, Service","Running","Automatic"\n'
)
OS_CSV = (
    '"Name","Version","BuildNumber","OSArchitecture","LastBootUpTime","ReleaseId"\n'
    '"Microsoft Windows Server 2022","10.0.20348","20348","64-bit","2026-10-01","2009"\n'
)
EVENT_CSV = (
    '"Level","Event"\n'
    '"Error","[Timestamp=2026-10-29] [Category=System] [EventID=7036] [Source=SCM] [Message=service stopped]"\n'
    '"Information","[Timestamp=2026-10-29] [Category=Application] [EventID=1000] [Source=App] [Message=ok]"\n'
)


# ---- the shared steps ----------------------------------------------------------------------------------------


def test_a_process_that_never_exits_is_stopped_after_the_timeout():
    clock = Clock()
    process_manager = FakeProcessManager(exit_code=None)

    with pytest.raises(guest_ops.GuestProcessTimeout, match="did not finish in 60 seconds"):
        guest_ops.run_powershell(process_manager, FakeVm(), None, "cmd", timeout=60, clock=clock, sleep=clock.sleep)

    assert process_manager.terminated == [42]
    assert clock.now >= 60


def test_the_poll_interval_backs_off_to_its_maximum():
    clock = Clock()
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        clock.now += seconds

    with pytest.raises(guest_ops.GuestProcessTimeout):
        guest_ops.run_powershell(FakeProcessManager(None), FakeVm(), None, "cmd", timeout=200, clock=clock, sleep=sleep)
    assert sleeps[:5] == [1.0, 2.0, 4.0, 8.0, guest_ops.POLL_MAX_SECONDS]
    assert max(sleeps) == guest_ops.POLL_MAX_SECONDS


def test_a_finished_process_returns_its_exit_code_without_waiting():
    clock = Clock()
    assert guest_ops.run_powershell(FakeProcessManager(exit_code=0), FakeVm(), None, "cmd", clock=clock, sleep=clock.sleep) == 0
    assert clock.now == 0.0


def test_a_process_the_guest_no_longer_lists_is_finished_with_an_unknown_exit_code():
    class Gone(FakeProcessManager):
        def ListProcessesInGuest(self, vm, creds, pids):
            return []

    assert guest_ops.run_powershell(Gone(), FakeVm(), None, "cmd") is None


def test_the_guest_budget_is_spent_after_its_time_and_warns_once(caplog):
    clock = Clock()
    budget = guest_ops.GuestBudget(seconds=100, clock=clock)
    assert budget.has_time() is True
    clock.now = 101
    assert budget.has_time() is False
    assert budget.has_time() is False
    assert budget.skipped == 2
    assert caplog.text.count("guest time budget") == 1


def test_a_failed_output_download_is_reported_as_none(monkeypatch):
    monkeypatch.setattr(guest_ops.guest_http, "get", lambda vm, url: FakeResponse(500))
    assert guest_ops.read_guest_output(FakeFileManager(), FakeVm(), None, "C:\\x.csv") is None


def test_a_failed_temp_folder_delete_does_not_raise():
    class Failing(FakeFileManager):
        def DeleteDirectoryInGuest(self, vm, creds, path, recursive):
            raise RuntimeError("guest gone")

    guest_ops.remove_temp_dir(Failing(), FakeVm(), None, "C:\\Windows\\Temp\\run-1")


# ---- services ------------------------------------------------------------------------------------------------


def test_a_service_display_name_with_a_comma_stays_in_one_field():
    rows = services.parse_services(SERVICE_CSV)
    assert [row.display_name for row in rows] == ["Print Spooler", "Microsoft Office Click-to-Run, Service"]
    assert rows[1].name == "ClickToRunSvc"
    assert rows[1].status == "Running"


def test_a_service_csv_without_a_column_is_refused():
    assert services.parse_services('"Name","Status"\n"x","Running"\n') is None


def test_an_empty_service_output_has_no_services():
    assert services.parse_services("  \n") == []


def test_services_are_published_per_display_name(monkeypatch):
    fake_vm_object = FakeVmObject()
    file_manager = FakeFileManager()
    monkeypatch.setattr(guest_ops, "transfer_file", lambda *a, **k: True)
    monkeypatch.setattr(guest_ops, "run_powershell", lambda *a, **k: 0)
    monkeypatch.setattr(guest_ops, "read_guest_output", lambda *a, **k: SERVICE_CSV)

    services.collect_vm_service_properties(
        fake_vm_object, FakeVm(), FakeContent(file_manager=file_manager), "u", "p", "")

    assert fake_vm_object.properties[
        "vCommunity|Guest OS|Services:Print Spooler|Service Name"] == "Spooler"
    assert fake_vm_object.properties[
        "vCommunity|Guest OS|Services:Microsoft Office Click-to-Run, Service|Service Start Type"] == "Automatic"
    assert file_manager.deleted == [file_manager.temp_dir]


def test_a_failed_service_download_publishes_nothing_and_still_cleans_up(monkeypatch):
    fake_vm_object = FakeVmObject()
    file_manager = FakeFileManager()
    monkeypatch.setattr(guest_ops, "transfer_file", lambda *a, **k: True)
    monkeypatch.setattr(guest_ops, "run_powershell", lambda *a, **k: 0)
    monkeypatch.setattr(guest_ops, "read_guest_output", lambda *a, **k: None)

    services.collect_vm_service_properties(fake_vm_object, FakeVm(), FakeContent(file_manager=file_manager), "u", "p", "")

    assert fake_vm_object.properties == {}
    assert file_manager.deleted == [file_manager.temp_dir]


def test_a_timed_out_service_step_is_a_warning_and_the_vm_is_skipped(monkeypatch, caplog):
    def timed_out(*args, **kwargs):
        raise guest_ops.GuestProcessTimeout("stopped")

    fake_vm_object = FakeVmObject()
    monkeypatch.setattr(guest_ops, "transfer_file", lambda *a, **k: True)
    monkeypatch.setattr(guest_ops, "run_powershell", timed_out)

    services.collect_vm_service_properties(fake_vm_object, FakeVm(), FakeContent(), "u", "p", "")

    assert fake_vm_object.properties == {}
    assert "Windows Service monitoring skipped" in caplog.text


def test_a_vm_that_is_not_a_running_windows_guest_is_skipped(monkeypatch):
    called = []
    monkeypatch.setattr(guest_ops, "transfer_file", lambda *a, **k: called.append(a) or True)
    services.collect_vm_service_properties(FakeVmObject(), FakeVm(tools="toolsNotRunning"), FakeContent(), "u", "p", "")
    assert called == []


# ---- OS information ------------------------------------------------------------------------------------------


def test_os_information_is_published_from_its_csv():
    fake_vm_object = FakeVmObject()
    os_info.publish_os_information(fake_vm_object, "win-01", OS_CSV)
    assert fake_vm_object.properties["vCommunity|Guest OS|Operating System|OS Name"] == "Microsoft Windows Server 2022"
    assert fake_vm_object.properties["vCommunity|Guest OS|Operating System|OS Release ID"] == "2009"


def test_os_information_with_a_missing_column_publishes_nothing(caplog):
    fake_vm_object = FakeVmObject()
    os_info.publish_os_information(fake_vm_object, "win-01", '"Name"\n"x"\n')
    assert fake_vm_object.properties == {}
    assert "has no" in caplog.text


# ---- event logs ----------------------------------------------------------------------------------------------


def test_every_event_level_has_its_criticality():
    assert events.criticality_for("Information") == Criticality.INFO
    assert events.criticality_for("Verbose") == Criticality.INFO
    assert events.criticality_for("Warning") == Criticality.WARNING
    assert events.criticality_for("Error") == Criticality.IMMEDIATE
    assert events.criticality_for("Critical") == Criticality.CRITICAL
    assert events.criticality_for("Something else") == Criticality.INFO


def test_the_event_message_has_both_brackets():
    assert events.format_event_message("Error", "disk failed") == "[WindowsEvent-Error disk failed]"


def test_events_are_published_with_their_level(monkeypatch):
    fake_vm_object = FakeVmObject()
    events.publish_events(fake_vm_object, "win-01", EVENT_CSV)
    assert [e["message"] for e in fake_vm_object.events][0].startswith("[WindowsEvent-Error [Timestamp=")
    assert fake_vm_object.events[0]["criticality"] == Criticality.IMMEDIATE
    assert len(fake_vm_object.events) == 2


def test_a_long_event_list_is_capped_per_vm_and_says_so(monkeypatch, caplog):
    monkeypatch.setattr(events, "MAX_EVENTS_PER_VM", 3)
    header = '"Level","Event"\n'
    rows = "".join(f'"Warning","event {i}"\n' for i in range(10))
    fake_vm_object = FakeVmObject()
    events.publish_events(fake_vm_object, "win-01", header + rows)
    assert len(fake_vm_object.events) == 3
    assert "has 10 Windows events" in caplog.text


def test_a_failed_temp_file_stops_before_the_script_runs_and_does_not_fail_with_none(monkeypatch, caplog):
    file_manager = FakeFileManager()
    ran = []
    monkeypatch.setattr(events.guest_ops, "create_temp_file", lambda *a, **k: (False, None))
    monkeypatch.setattr(events.guest_ops, "run_powershell", lambda *a, **k: ran.append(a) or 0)

    events.collect_windows_events(FakeVmObject(), FakeVm(), FakeContent(file_manager=file_manager), "u", "p", "<x/>")

    assert ran == []
    assert "NoneType" not in caplog.text
    assert file_manager.deleted == [file_manager.temp_dir]


def test_a_full_event_collection_publishes_the_events(monkeypatch):
    fake_vm_object = FakeVmObject()
    monkeypatch.setattr(events.guest_ops, "create_temp_file", lambda *a, **k: (True, "C:\\T\\EventLog-TEMP\\events.xml"))
    monkeypatch.setattr(events.guest_ops, "file_exists", lambda *a, **k: True)
    monkeypatch.setattr(events.guest_ops, "transfer_file", lambda *a, **k: True)
    monkeypatch.setattr(events.guest_ops, "run_powershell", lambda *a, **k: 0)
    monkeypatch.setattr(events.guest_ops, "read_guest_output", lambda *a, **k: EVENT_CSV)

    events.collect_windows_events(fake_vm_object, FakeVm(), FakeContent(), "u", "p", "<Events/>")

    assert len(fake_vm_object.events) == 2
