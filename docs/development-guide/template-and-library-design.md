# Template and Content Library Design

**Status: built in the code, not yet installed or verified on the test instance.** `Content Library`, `Library Item` and `VM Template` are in `definition.py` and written by `collectors/library/`. Unit tests cover them with fakes (`tests/test_library_collection.py`, `tests/test_vm_template.py`). Not built: the VM-to-template children, the template storage metric on the Datastore, and the library sync-age metric. The model of the objects is in [Templates and Content Libraries](../concepts/templates-and-content-libraries.md). The open items are on the [To Do project](https://github.com/users/e1-rahabok/projects/1).

## Verified on the test instance (read-only)

- VCF Operations has **no content library object and no library item object**. The vCenter adapter's objects are the kinds the pack already reads, plus `VirtualMachine`.
- **Folders in VCF Operations (VMWARE adapter), by object count:** there are four folder types, one per folder kind: `HostFolder` (Compute, 0 objects), `NetworkFolder` (Network, 21), `DatastoreFolder` (Storage, 0) and `VMFolder` (VM, 6). Their kind type is `TAG`, and they do have objects. The general `Folder` kind has 0 objects, so it is not used.
- **A template is a VirtualMachine in VCF Operations.** There is no template object type. A template VM has a `VMFolder` object as its parent, and a status object, `VM Entity Status:Template`, that marks it as a template. Its child in the relation list is its Datastore.
- **vSphere, read-only (vCenter 10.115.1.87):** each VM template sits in a VM folder (`Folder`), which sits in the Datacenter. Each template is registered to a host and holds its disks on a datastore. Those are relations, not containers. Both content libraries are **subscribed** (`type` = `SUBSCRIBED`), and each stores its items on a datastore. Each library is held by the vCenter (`server_guid`), not by a folder. Each subscription points at a published library on the internet: `supervisor-library` at `https://wp-content.broadcom.com/supervisor/v1/latest/lib.json` and `cl-vks01` at `https://wp-content.broadcom.com/v2/latest/lib.json`. Both have automatic sync and on-demand sync enabled, and no authentication.
- Five VirtualMachine objects have `summary|config|isTemplate` = `true`. Two queries gave 139 and 142 VirtualMachine objects, so that count is not settled. Name matching is not reliable: six names contain "template", and one of them is not a template.
- **No VCF Operations property links a VM to the template it came from.** Over 20 VMs there were 364 property names, none of them a source. The closest are `summary|folder`, `summary|datastore`, `summary|parentHost` and the template flag.
- The content libraries, read from vCenter through the vSphere Automation API:

| Library | Items | Item types | Not stored locally (`cached` = false) |
| :--- | :--- | :--- | :--- |
| `497d9b6a…` (cl-vks01) | 138 | `ovf`: 138 | 138 |
| `479fa23e…` | 7 | `ovf`: 2, `other`: 5 | 6 |

- In the lab there are 145 items, 3.9 GB in total. All 145 have `security_compliance` = true, and all 145 have a `source_id`. The `source_id` on local items is to be checked, because the documentation says it is null for local items.
- No item of type `vm-template` or `iso` was seen.
- The item list call returns **only item IDs**. Each item needs its own get call to read its size, state and compliance.
- Item fields: `creation_time`, `last_modified_time`, `last_sync_time`, `certificate_verification_info`, `description`, `type`, `version`, `content_version`, `library_id`, `size`, `cached`, `name`, `security_compliance`, `id`, `source_id`, `metadata_version`.

## Decisions

- **Approved on 2026-10-28:** read the content libraries from vCenter through the vSphere Automation API. This is a second connection to vCenter, next to the pyVmomi calls the pack makes today.
- **One object type for all library items.** The object type is `Library Item`, with `Type` as a property. It covers every type: `ovf`, `ova`, `vm-template`, `iso`, `other` and any type not seen yet. Excluding a type would hide items. The lab already has five items of type `other`, which a subset of `ovf` and `ova` would have dropped. The type costs nothing as a property.
- **Subscribed-library sync-age metric:** later. It is on the [To Do project](https://github.com/users/e1-rahabok/projects/1).

## Still open

1. **What links a VM to its template?** The relation is real: one template has many VMs, and a VM has at most one template. VCF Operations does not store it (see above), so the pack needs another source. The options are:
   - **vCenter task history.** A clone task records its source template. This is a read from vCenter beyond the library read, so it needs your approval. How long vCenter keeps task history is to be verified.
   - **A VM annotation or custom attribute** set by the tool that provisions the VM. It works only for VMs made by that tool.

   Until one is chosen, the VM Template object can be built without its children.

## Object types

All three are created by the pack under its own adapter kind, `vCommunity`, with `define_object_type`. They do not change the vCenter adapter's objects. Keys have no special characters.

| Object type | Created from | Lab count |
| :--- | :--- | :--- |
| `Content Library` | vSphere Automation API, one per library | 2 |
| `Library Item` | vSphere Automation API, every item of every library, all types | 145 |
| `VM Template` | VCF Operations VirtualMachine objects with the template flag | 5 |

## Parent and child relationships

The SDK has `add_parent` and `add_child`, so a pack object can be a child of an existing object, and a parent can have many children.

| Object | Parent | Children |
| :--- | :--- | :--- |
| vCenter object (existing) | none | `Content Library` |
| `Content Library` | the vCenter object (existing, kind `vCenter`) | `Library Item` |
| `Library Item` | its `Content Library` | none |
| `VM Template` | the `VMFolder` object (existing, "Virtual Machine Folder") that the template VM is in. VCF Operations already lists it as the parent of the template VM. The Datastore is a child in the relation list, not a parent. | the VMs (existing VirtualMachine objects) cloned from it |
| VM (existing) | the `VM Template` it came from, if the source is known | none |

Notes:

- **Cardinality:** one `VM Template` has many VMs, and a VM has at most one `VM Template`. In the SDK, the template is the parent, so the template calls `add_child` for each of its VMs.
- A library item has no link in the API to the inventory template it came from, so no relationship is made between a `Library Item` and a `VM Template`. The library is the parent of the item.
- **Subscription:** a subscribed `Content Library` is linked to a published library on the internet, through its subscription URL. That published library is not an object in VCF Operations, so it is not a parent or child. It is a property of the `Content Library`. A `Library Item` links to its published item through `source_id`, which is a property too.
- Whether VCF Operations accepts a link from a pack object to an existing object that is not in the same result is not verified. It is a check in the first build (see [Verification](#verification)).

## Properties

Properties are text, published under `vCommunity|`. Only the keys that VCF Operations returns are published, so a property is not added until its key is seen in a response.

| Object | Properties |
| :--- | :--- |
| `Content Library` | Name, Library ID, Type (`SUBSCRIBED` or local), Subscription URL (`subscription_info.subscription_url`), Automatic Sync, State |
| `Library Item` | Name, Library ID, Type, Description, Version, Content Version, Size (GB), Stored Locally (`cached`), Security Compliant (`security_compliance`), Certificate Verification (`certificate_verification_info.status`), Last Modified, Last Sync, Source Item ID (`source_id`) |
| `VM Template` | Guest OS, VMware Tools status, Hardware Version, vCPUs, Memory (GB), Disk Used (GB), Encryption, Datastore name, VM folder. The VCF Operations keys for these are to be checked. |

## Metrics

Metrics are numbers, published on the object, and can be charted and alerted on.

| Object | Metric | Meaning |
| :--- | :--- | :--- |
| `Content Library` | Items | Number of items |
| `Content Library` | Items Not Stored Locally | Items with `cached` = false |
| `Content Library` | Items Not Security Compliant | Items with `security_compliance` = false |
| `Content Library` | Total Size (GB) | Sum of `size` of the items |
| `Library Item` | Size (GB) | `size` in GiB |
| `VM Template` | Disk Used (GB) | Disk space of the template VM |
| `VM Template` | Number of VMs | Its VMs, once the source of the link is chosen |
| Datastore (existing object) | Template Storage (GB) | Total disk space of the VM templates on the datastore |

A template VM cannot run, so it has no performance statistics and no KPI is proposed for it.

## Efficiency

- **VM Template: no new call.** `summary|config|isTemplate` is added to the property list that the pack already reads in one batched call for all VMs (`read_vms`). The cost is one object per template.
- **Content library: one request per item.** The item list returns IDs only, so the state, size and compliance of each item need one get call each. In the lab that is 145 get calls per full read. This cannot be avoided if those fields are needed.
- **Read on a long window.** Libraries change rarely. Read them once an hour, like the Periodic Cluster Check, and keep the last values between reads, so the cycle does not make these calls. The interval is a design choice. Measure one full read before fixing it.
- **A second session.** The vSphere Automation API has its own session, separate from the pyVmomi connection, and uses the same account as the Adapter Instance.

## Verification

Done with a read-only probe, before any build:

1. The VCF Operations keys of the template properties (Guest OS, VMware Tools, Hardware Version and the rest), on one template VM.
2. Whether a library item's `source_id` is set for local items, to tell whether these libraries are subscribed.
3. The time of one full library read, for the interval.

Done with a build on the test instance, after an approved install:

4. Whether a pack-created object of its own kind shows in VCF Operations, with a parent link to an existing VirtualMachine or Datastore object.
5. Whether a pack-created object survives a collection cycle, and what happens to an object the pack stops reporting. The parent link is a separate test.

## Not in this design

Alerts and events for templates and libraries.
