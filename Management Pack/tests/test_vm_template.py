#  Copyright 2026 VCF Operations vCommunity Management Pack
"""VM Template: built only for a VM marked as a template, with its folder as the parent.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from aria.ops.object import Key, Object
from aria.ops.result import CollectResult
from collectors.library import collectTemplateData as tpl

GIB = 1024 ** 3


def fake_vm(moid="vm-7", name="rhel-template", parent_moid="group-v3", parent_name="ocp-cl01"):
    return SimpleNamespace(_moId=moid, name=name, parent=SimpleNamespace(_moId=parent_moid, name=parent_name))


def template_props(**overrides):
    props = {
        "config.template": True,
        "config.guestFullName": "Red Hat Enterprise Linux 9 (64-bit)",
        "config.version": "vmx-21",
        "summary.config.numCpu": 4,
        "summary.config.memorySizeMB": 8192,
        "summary.storage.committed": 20 * GIB,
        "datastore": [SimpleNamespace(name="ds-nvme02")],
    }
    props.update(overrides)
    return props


def folder_object(moid="group-v3"):
    folder = Object(Key("VMWARE", "VMFolder", "ocp-cl01", []))
    return folder


def test_a_vm_that_is_not_a_template_gets_no_object():
    result = CollectResult()
    out = tpl.publish_vm_template(fake_vm(), template_props(**{"config.template": False}), "vm", "uuid-1", {}, result)
    assert out is None
    assert len(result.objects) == 0


def test_a_template_gets_its_properties_and_disk_metric():
    result = CollectResult()
    template = tpl.publish_vm_template(fake_vm(), template_props(), "rhel-template", "uuid-1", {}, result)
    assert template is not None
    assert template.get_key().object_kind == "VM Template"
    assert template.get_last_property_value(f"vCommunity|{tpl.TEMPLATE_KIND}|Guest OS") == "Red Hat Enterprise Linux 9 (64-bit)"
    assert template.get_last_property_value(f"vCommunity|{tpl.TEMPLATE_KIND}|Hardware Version") == "vmx-21"
    assert template.get_last_property_value(f"vCommunity|{tpl.TEMPLATE_KIND}|vCPUs") == "4"
    assert template.get_last_property_value(f"vCommunity|{tpl.TEMPLATE_KIND}|Memory (GB)") == "8.0"
    assert template.get_last_property_value(f"vCommunity|{tpl.TEMPLATE_KIND}|Datastore") == "ds-nvme02"
    assert template.get_last_property_value(f"vCommunity|{tpl.TEMPLATE_KIND}|VM Folder") == "ocp-cl01"
    assert template.get_last_metric_value(f"vCommunity|{tpl.TEMPLATE_KIND}|Disk Used (GB)") == 20.0


def test_the_template_is_a_child_of_its_vm_folder():
    result = CollectResult()
    folder = folder_object("group-v3")
    template = tpl.publish_vm_template(
        fake_vm(), template_props(), "rhel-template", "uuid-1", {"group-v3": folder}, result
    )
    assert template.get_parents() == {folder.get_key()}


def test_no_folder_found_means_no_parent_but_the_template_is_still_published():
    result = CollectResult()
    template = tpl.publish_vm_template(fake_vm(), template_props(), "rhel-template", "uuid-1", {}, result)
    assert template.get_parents() == set()
    assert len(result.objects) == 1


def test_identifiers_include_the_vcenter_so_two_vcenters_do_not_clash():
    result = CollectResult()
    a = tpl.publish_vm_template(fake_vm(), template_props(), "rhel-template", "uuid-A", {}, result)
    b = tpl.publish_vm_template(fake_vm(), template_props(), "rhel-template", "uuid-B", {}, result)
    assert a.get_key() != b.get_key()
