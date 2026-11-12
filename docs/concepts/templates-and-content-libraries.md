# Templates and Content Libraries

vSphere has two kinds of template. One is a VM in the vCenter inventory, the other is a package in a **content library**. They are different objects stored in different places.

The VMware vCenter adapter of VCF Operations shows only the first kind, as an ordinary VirtualMachine. The pack adds three object types of its own, so both kinds can be seen and reported on: **Content Library**, **Library Item** and **VM Template**. How they are built is described in [Template and Content Library Design](../development-guide/template-and-library-design.md), and their keys are listed in [Metrics and Properties](../reference/metrics-and-properties.md).

## The two kinds of template

| | VM Template | OVF & OVA Template |
| :--- | :--- | :--- |
| What it is | A virtual machine in the vCenter inventory that has been converted into a template. It can't be powered on. | A library item: an OVF or OVA package stored as files in a content library. It is not in the inventory. |
| Where it lives | In the vCenter inventory, in a VM folder, with its disks on a datastore | Only in a content library |
| Used to | Clone a VM in the same vCenter | Deploy a VM in the same vCenter or another one |
| Icon in the vSphere Client | A stacked VM icon | A package icon in the library's item list |
| Versioning | Only when the template is also in a content library | Always, through the item's content version |
| In the vCenter adapter of VCF Operations | A VirtualMachine object with `summary|config|isTemplate` = true | Not present |
| Added by the pack | A **VM Template** object | A **Library Item** object, in its **Content Library** |

An OVF & OVA template is not a VM. Its name, size, sync state and version belong to the library, not to a host or a datastore.

## Content library

A content library holds library items and belongs to one vCenter. It is one of two types:

- **Local**: its items are created and stored in this library.
- **Subscribed**: its items are synchronised from a published library, so each item has a source item.

Each library item has a type (such as `ovf`, `ova`, `vm-template`, `iso` or `other`), a size, a content version, and a flag that says whether its files are stored locally (cached). A subscribed item can be out of date with its source. An item can also be checked for security compliance.

A VM template in the inventory and a library item are linked only by the operation that created one from the other, for example cloning a VM into a library as a template. The item model in the vSphere Automation API has no field that points to the inventory VM it came from.

## How they relate

```
vCenter
 ├── Datacenter ── VM folder ── VM Template (inventory)     ← a VirtualMachine with isTemplate = true
 │                              on a Datastore, on a Host
 └── Content Library (local or subscribed)
       ├── OVF & OVA Template (library item)
       └── VM template stored in the library (library item of type vm-template)
```

One VM template can be the source of many VMs, and a VM comes from at most one template. vSphere does not record this link on the VM, and VCF Operations does not store it either, so the pack can't show it yet. See [Still open](../development-guide/template-and-library-design.md#still-open).

## Source

- [Content Library ItemModel, vSphere Automation API 9.1](https://developer.broadcom.com/xapis/vsphere-automation-api/9.1/data-structures/Content%20Library%20ItemModel/): the item fields `name`, `type`, `size`, `cached`, `content_version`, `last_sync_time`, `source_id`, `security_compliance` and `certificate_verification_info`.
