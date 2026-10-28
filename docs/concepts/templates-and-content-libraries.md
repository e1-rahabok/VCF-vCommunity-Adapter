# Templates and Content Libraries

vSphere has two kinds of template, and both are kept in a **content library**. They are different objects, stored in different places, and the pack currently sees only one of them.

This page is the model: what each object is, and how they relate. The plan for showing them in VCF Operations is in [Template and Content Library Design](../development-guide/template-and-library-design.md).

## The two kinds of template

| | VM Template | OVF & OVA Template |
| :--- | :--- | :--- |
| What it is | A virtual machine in the vCenter inventory, converted into a template. It cannot be powered on. | A library item: an OVF or OVA package stored as files in a content library. It is not in the inventory. |
| Where it lives | In the vCenter inventory, in a VM folder, on a datastore | In a content library only. It exists only when it is in a library. |
| Used to | Clone a VM from it, in the same vCenter | Deploy a new VM from it, in the same or another vCenter |
| Icon in vSphere Client | A stacked VM icon | A package icon in the library's list |
| Versioning | Only when the template is in a published or local content library | Always, through the content version of the item |
| In VCF Operations today | A VirtualMachine object of the vCenter adapter, with `summary|config|isTemplate` = true | Not present. VCF Operations has no content library and no library item objects. |

An OVF & OVA template is not a VM. Its name, size, sync state and version belong to the library, not to a host or datastore.

## Content library

A content library is a container of library items, and it belongs to one vCenter. It is either:

- **Local**: its items are created and stored in this library.
- **Subscribed**: its items are synchronised from a published library, so each item has a source item.

Each library item has a type, a size, a content version, and a state of whether its files are stored locally (cached). A subscribed item can be out of date with its source. An item can also be checked for security compliance.

A VM template in the inventory and a library item are related only through the action that creates one from the other: a VM can be cloned to a library as a template. The item model in the vSphere Automation API has no field that names the inventory VM it came from. The link is a fact of the operation, not a stored reference.

## How they relate

```
vCenter
 ├── Datacenter ── VM folder ── VM Template (inventory)     ← a VirtualMachine, isTemplate = true
 │                              on Datastore, on Host
 └── Content Library (local or subscribed)
       ├── OVF & OVA Template (library item)
       └── VM template in the library (library item; the type value is to verify)
```

The vSphere Client shows the library as a tree node. In the screenshots taken on the lab, the library `cl-vks01` has 138 OVF & OVA templates and no VM templates in its VM Templates tab. The template `vcf-services-runtime-template-9.1.1.0.25714471` is an inventory VM template, under the `vcf-automation` folder, and its Versioning tab explains that versioning needs a library.

## Source

- [Content Library ItemModel, vSphere Automation API 9.1](https://developer.broadcom.com/xapis/vsphere-automation-api/9.1/data-structures/Content%20Library%20ItemModel/): the item fields: `name`, `type`, `size`, `cached`, `content_version`, `last_sync_time`, `source_id`, `security_compliance` and `certificate_verification_info`.
