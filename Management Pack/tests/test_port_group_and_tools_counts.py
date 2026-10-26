#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Number of Port Groups (vCenter and vSphere World) and the VMware Tools counts on vSphere World.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.vcenter import vcenter_port_groups as vpg
from metrics.world import port_group_counts as pg
from metrics.world import vm_tools_counts as tools
from utils import ops_stats


# --- Number of Port Groups on one vCenter, per Datacenter ---------------------------------------------------------

def test_same_name_on_several_hosts_of_one_datacenter_counts_once():
    # Standard port groups: "VM Network" on two hosts is one port group in the Datacenter.
    names = {"datacenter-1": [["VM Network", "Management"], ["VM Network", "vMotion", "iSCSI"]]}
    assert vpg.count_port_groups(names) == 4


def test_same_name_in_two_datacenters_counts_twice():
    names = {"datacenter-1": [["VM Network"]], "datacenter-2": [["VM Network"]]}
    assert vpg.count_port_groups(names) == 2


def test_distributed_and_standard_with_the_same_name_in_one_datacenter_count_once():
    # One name in the namespace of one Datacenter: a single port group.
    names = {"datacenter-1": [["prod-vlan-100"], ["prod-vlan-100", "vMotion"]]}
    assert vpg.count_port_groups(names) == 2


def test_distributed_port_groups_with_the_same_name_in_two_datacenters_count_twice():
    # A distributed port group name repeats across Datacenters of one vCenter: two port groups.
    names = {"datacenter-1": [[], ["pod-default-x"]], "datacenter-2": [[], ["pod-default-x", "pod-default-y"]]}
    assert vpg.count_port_groups(names) == 3


def test_a_datacenter_with_no_port_groups_counts_zero():
    assert vpg.count_port_groups({"datacenter-1": [[], []]}) == 0


def test_no_datacenters_gives_zero():
    assert vpg.count_port_groups({}) == 0


def test_metric_key_is_the_one_the_world_reads():
    assert vpg.METRIC_KEY == pg.METRIC_KEY == "vCommunity|Number of Port Groups"


# --- Number of Port Groups on vSphere World: the sum of the vCenters' last values ---------------------------------

def test_world_total_adds_the_vcenters_that_have_a_value():
    values = {
        "vc-a": {pg.METRIC_KEY: 120.0},
        "vc-b": {pg.METRIC_KEY: 45.0},
        "vc-c": {},                       # never published: left out
    }
    assert pg.total(values) == 165


def test_world_total_with_no_values_is_zero():
    assert pg.total({"vc-a": {}}) == 0


def test_port_group_count_uses_the_configuration_limit_not_the_ten_minute_one():
    # Only the port group count uses the 15-minute limit. Every other metric keeps the 10-minute limit.
    assert ops_stats.CONFIGURATION_STALE_AFTER_MINUTES == 15
    assert ops_stats.STALE_AFTER_MINUTES == 10


# --- Number of VM without Tools and Number of VMware Tools down ---------------------------------------------------

def row(version=None, running=None, power=None):
    values = {}
    if version is not None:
        values[tools.VERSION_KEY] = version
    if running is not None:
        values[tools.RUNNING_KEY] = running
    if power is not None:
        values[tools.POWER_KEY] = power
    return values


def test_vm_without_tools_is_counted_whatever_its_power_state():
    rows = [
        row(version="Guest Tools Not Installed", running="Guest Tools Not Running", power="Powered On"),
        row(version="Guest Tools Not Installed", running="Guest Tools Not Running", power="Powered Off"),
        row(version="Guest Tools Unmanaged", running="Guest Tools Running", power="Powered On"),
    ]
    assert tools.tools_counts(rows) == (2, 0)


def test_tools_down_needs_installed_tools_not_running_and_powered_on():
    rows = [
        row(version="Guest Tools Unmanaged", running="Guest Tools Not Running", power="Powered On"),
        row(version="Guest Tools Too Old", running="Guest Tools Not Running", power="Powered On"),
    ]
    assert tools.tools_counts(rows) == (0, 2)


def test_powered_off_vm_with_a_stale_not_running_value_is_not_down():
    # The lab instance has 29 powered-off VMs whose last value is "not running". They are not Tools problems.
    rows = [row(version="Guest Tools Unmanaged", running="Guest Tools Not Running", power="Powered Off")]
    assert tools.tools_counts(rows) == (0, 0)


def test_tools_running_is_not_down():
    rows = [row(version="Guest Tools Current", running="Guest Tools Running", power="Powered On")]
    assert tools.tools_counts(rows) == (0, 0)


def test_missing_values_are_not_counted():
    # A template, or a VM with no stored Tools value: left out of both counts.
    rows = [row(), row(power="Powered On"), row(running="Guest Tools Not Running", power="Powered On")]
    assert tools.tools_counts(rows) == (0, 0)


def test_installed_but_version_unknown_is_not_counted_as_down():
    # Without a version value, we do not know Tools are installed, so the VM is not counted as down.
    rows = [row(running="Guest Tools Not Running", power="Powered On")]
    assert tools.tools_counts(rows) == (0, 0)
