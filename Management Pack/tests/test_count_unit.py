#  Copyright 2026 VCF Operations vCommunity Management Pack
"""TEST (0.6.7 build only): the unit "count", on the two share properties and the test metric.

Remove this file, and the TEST lines in vm_shares.py and definition.py, once the result is known.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from aria.ops.object import Key, Object
from aria.ops.result import CollectResult
from properties.vm import vm_shares
from utils.ops_inventory import VmInfo


def vm_definition_entries():
    import definition
    tree = definition.get_adapter_definition().to_json()
    found = {}

    def walk(node, parent_key):
        if isinstance(node, dict):
            key = node.get("key")
            if key in (vm_shares.CPU_PROPERTY, vm_shares.MEMORY_PROPERTY, vm_shares.TEST_METRIC) and parent_key == "Configuration":
                found[key] = node
            for value in node.values():
                walk(value, key if key else parent_key)
        elif isinstance(node, list):
            for item in node:
                walk(item, parent_key)

    walk(tree, None)
    return found


def test_count_unit_is_defined_as_count():
    assert vm_shares.COUNT_UNIT.value.key == "count"
    assert vm_shares.COUNT_UNIT.value.label == "count"


def test_definition_carries_the_count_unit_on_both_properties_and_the_metric():
    entries = vm_definition_entries()
    assert set(entries) == {vm_shares.CPU_PROPERTY, vm_shares.MEMORY_PROPERTY, vm_shares.TEST_METRIC}
    for key, node in entries.items():
        assert node["unit"] == "count", key


def test_the_test_metric_is_published_with_the_property_value():
    obj = Object(Key("VMWARE", "VirtualMachine", "edge01", []))
    vm = VmInfo(id="x", name="edge01", moid="vm-1", host_name="h", powered_on=True, vcpus=8.0, memory_mb=32768.0)
    vm_shares.collect_vm_shares(
        obj, "edge01", vm, {vm_shares.CPU_SHARES: 16000.0, vm_shares.MEMORY_SHARES: 327680.0}
    )
    assert obj.get_last_property_value(f"vCommunity|Configuration|{vm_shares.CPU_PROPERTY}") == 2000.0
    assert obj.get_last_metric_value(f"vCommunity|Configuration|{vm_shares.TEST_METRIC}") == 2000.0
