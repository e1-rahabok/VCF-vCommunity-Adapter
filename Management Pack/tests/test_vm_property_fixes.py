#  Copyright 2026 VCF Operations vCommunity Management Pack
"""VM Tools settings (issue #80) and virtual disks on a VM with no network adapter (issue #81).

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from pyVmomi import vim

from fakes import FakeObject
from properties.vm.vm_configurations import collect_vm_configurations
from properties.vm.vm_disk import collect_vm_disk


def test_tools_settings_are_read_from_the_requested_paths():
    vm = FakeObject("vm")
    collect_vm_configurations(vm, {"config.tools.syncTimeWithHost": True,
                                   "config.tools.toolsUpgradePolicy": "manual"}, "vm")
    assert vm.properties["vCommunity|Guest|Tools Sync Time"] == "True"
    assert vm.properties["vCommunity|Guest|Tools Upgrade Policy"] == "manual"


def test_a_vm_with_no_network_adapter_still_gets_its_virtual_disks():
    disk = vim.vm.device.VirtualDisk()
    disk.key = 2000
    disk.controllerKey = 1000
    disk.deviceInfo = vim.Description(label="Hard disk 1", summary="")
    vm = FakeObject("vm")
    collect_vm_disk(vm, {"config.hardware.device": [disk]}, "vm")
    assert any("Hard disk 1" in key for key in vm.properties), vm.properties
