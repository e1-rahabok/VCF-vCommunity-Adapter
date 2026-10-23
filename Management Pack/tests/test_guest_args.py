#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Windows Service names from the configuration file cannot break out of the PowerShell command.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from utils import guest_args

REAL_NAMES = ["Dhcp", "WinDefend", "Dnscache", "MpsSvc", "W32Time", "MSSQL$SQLEXPRESS", "SQLAgent$MY-INST_1",
              "vmicheartbeat", "Windows Time", "NetTcpPortSharing", "wuauserv", "_Internal.Svc"]

INJECTIONS = [
    "x'; Remove-Item C:\\ -Recurse -Force; '",
    "x'",
    "'x",
    'x"; calc; "',
    "x`n",
    "$(calc)",
    "x$(calc)",
    "x; calc",
    "x | calc",
    "x & calc",
    "x > C:\\out.txt",
    "x\nRemove-Item",
    "x\r",
    "Dhcp\n",                 # a new line at the end
    "x\u2018; calc; \u2019",   # curly single quotes: PowerShell reads them as quotes
    "x\u201c; calc",           # curly double quotes
    "Win*",                    # a wildcard would select every service that matches
    "Wi?Time",
    "[a-z]*",
    "{calc}",
    "%COMSPEC%",
    "",
    " ",
    "-Command",                # starts with a dash
    "a" * 257,
    None,
    42,
]


@pytest.mark.parametrize("name", REAL_NAMES)
def test_real_service_names_are_accepted(name):
    assert guest_args.is_safe_service_name(name)


@pytest.mark.parametrize("name", INJECTIONS)
def test_names_that_could_break_out_are_refused(name):
    assert not guest_args.is_safe_service_name(name)


def test_the_command_text_is_the_same_as_before_for_real_names():
    """The old code built "@('a', 'b')" itself. The text must not change for names that were fine."""
    assert guest_args.powershell_string_array(["Dhcp", "WinDefend"]) == "@('Dhcp', 'WinDefend')"
    assert guest_args.powershell_string_array([]) == "@()"
    assert guest_args.powershell_string_array(["MSSQL$SQLEXPRESS"]) == "@('MSSQL$SQLEXPRESS')"


@pytest.mark.parametrize("bad", INJECTIONS)
def test_building_the_command_with_an_unsafe_name_fails_closed(bad):
    with pytest.raises(ValueError, match="Not a safe"):
        guest_args.powershell_string_array(["Dhcp", bad])


def test_safe_names_keeps_the_good_ones_in_order_and_logs_the_rest_once(caplog):
    with caplog.at_level(logging.WARNING, logger=guest_args.logger.name):
        kept = guest_args.safe_service_names(["Dhcp", "x'; calc; '", "WinDefend", "Win*"])
    assert kept == ["Dhcp", "WinDefend"]
    assert len(caplog.records) == 1
    assert "calc" in caplog.text and "Win*" in caplog.text


def test_nothing_to_log_when_every_name_is_fine(caplog):
    with caplog.at_level(logging.WARNING, logger=guest_args.logger.name):
        assert guest_args.safe_service_names(REAL_NAMES) == REAL_NAMES
    assert caplog.records == []


def test_an_empty_or_missing_list_is_an_empty_list():
    assert guest_args.safe_service_names([]) == []
    assert guest_args.safe_service_names(None) == []


def test_the_collector_builds_its_command_through_the_checked_function():
    """vmService.py must not build the array itself again."""
    source = (Path(__file__).resolve().parents[1] / "app" / "properties" / "vm" / "vmService.py").read_text(encoding="utf-8")
    assert "guest_args.powershell_string_array(" in source
    assert 'f"\'{s}\'"' not in source
