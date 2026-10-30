#  Copyright 2026 VCF Operations vCommunity Management Pack

"""VM Template: a virtual machine that is marked as a template in vCenter, published as an object of its own.

It is built from the VM data the VM collector already reads, so it costs no extra call. It has no parent link: the
Virtual Machine Folder it sits in is not part of the result, and under the PER_OBJECT relationship mode its links
cannot be written without replacing the folder's other children. See docs/development-guide/template-and-library-design.md.
The children, the VMs cloned from the template, are not built yet: VCF Operations does not store that link.
"""

from typing import Any, Dict, Optional

from aria.ops.object import Identifier, Key, Object
from aria.ops.result import CollectResult
from constants.main import ADAPTER_KIND

TEMPLATE_KIND = "VM Template"
GIB = 1024 ** 3

# The VM property paths this module reads. The VM collector adds them to its batch read.
PROPERTY_PATHS = [
    "config.template",
    "config.guestFullName",
    "config.version",
    "summary.config.numCpu",
    "summary.config.memorySizeMB",
    "summary.storage.committed",
    "datastore",
]


def publish_vm_template(
    vm_ref: Any,
    prop_dict: Dict[str, Any],
    vm_name: str,
    vcenter_uuid: str,
    result: CollectResult,
) -> Optional[Object]:
    """Adds a VM Template object for a VM that is marked as a template. Returns None for any other VM.

    vm_ref: the vim.VirtualMachine. prop_dict: its property values, by path, from PROPERTY_PATHS.
    """
    if not prop_dict.get("config.template"):
        return None

    template = Object(
        Key(
            ADAPTER_KIND,
            TEMPLATE_KIND,
            vm_name,
            [Identifier("VMEntityObjectID", vm_ref._moId), Identifier("VMEntityVCID", vcenter_uuid)],
        )
    )
    template.with_property(f"vCommunity|{TEMPLATE_KIND}|Guest OS", str(prop_dict.get("config.guestFullName") or ""))
    template.with_property(f"vCommunity|{TEMPLATE_KIND}|Hardware Version", str(prop_dict.get("config.version") or ""))
    template.with_property(f"vCommunity|{TEMPLATE_KIND}|vCPUs", str(prop_dict.get("summary.config.numCpu") or 0))
    template.with_property(f"vCommunity|{TEMPLATE_KIND}|Memory (GB)", str(round(float(prop_dict.get("summary.config.memorySizeMB") or 0) / 1024, 2)))
    template.with_property(f"vCommunity|{TEMPLATE_KIND}|Datastore", ", ".join(ds.name for ds in (prop_dict.get("datastore") or [])))
    template.with_property(f"vCommunity|{TEMPLATE_KIND}|VM Folder", vm_ref.parent.name if vm_ref.parent is not None else "")
    template.with_metric(f"vCommunity|{TEMPLATE_KIND}|Disk Used (GB)", round(float(prop_dict.get("summary.storage.committed") or 0) / GIB, 2))

    result.add_object(template)
    return template
