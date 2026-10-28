# Template and Content Library Design

**Status: design only, not built.** It describes three object types the pack would add, and what is still to be decided before building. The model of the objects is in [Templates and Content Libraries](../concepts/templates-and-content-libraries.md).

## What is verified and what is not

Verified on the test instance, read-only, on 2026-10-28:

- VCF Operations has **no content library object and no library item object** under the vCenter adapter. The vCenter adapter's resource kinds are the ones the pack already reads, plus `VirtualMachine`, `Datastore`, `ResourcePool`, `NamespaceV2` and similar. None is a library.
- The VirtualMachine objects include templates. Five of them have `summary|config|isTemplate` = `true`. The count of VirtualMachine objects differed between two queries (139 and 142), so it is not a settled number.
- A template's name does not identify it. Six names contain the word "template", but only five are flagged. Use the flag.

Not yet verified (each is a check in the first build, see [Verification](#verification)): the VCF Operations property names of a template VM; whether the vSphere Automation API's list call returns the item fields, or each item needs its own call; whether a relationship from a pack object to a vCenter object is accepted when the vCenter object is not in the same result.

## Decision needed first

**VCF Operations does not hold content library data, so the pack would have to read the library from vCenter.** Libraries are only in the vSphere Automation API, which is a second API next to the pyVmomi calls the pack uses today. This is a direct read from vCenter for data VCF Operations does not have. Under the rule in this project, that is not allowed without an explicit decision. Nothing below should be built until the decision is made.

An earlier answer said the efficiency was fine because the template data is already in VCF Operations. That is true only of the VM templates. It is not true of the content libraries, which are the larger part of the design.

## Object types

All three are created by the pack under its own adapter kind, `vCommunity`, with `define_object_type`. They do not change the vCenter adapter's objects. Naming: keys without `&`, so the key is `OVF OVA Template`, with the label `OVF & OVA Template`.

| Object type | Created from | Count in the lab |
| :--- | :--- | :--- |
| Content Library | vSphere Automation API, the libraries of each vCenter | 1 seen in the screenshots (`cl-vks01`) |
| OVF OVA Template | vSphere Automation API, the library items of type ovf or ova | 138 in `cl-vks01` |
| VM Template | VCF Operations VirtualMachine objects with the template flag | 5 |

Whether a VM template in a library (type `vm-template`) is a fourth type, or part of Content Library, is open.

## Parent and child relationships

The SDK has `add_parent` and `add_child`, so a pack object can be a child of an existing object.

| Object | Parent (existing object) | Children |
| :--- | :--- | :--- |
| Content Library | the vCenter object (the `VMwareAdapter Instance` and `vCenter` objects are already in the result) | OVF OVA Template, VM Template items |
| OVF OVA Template | its Content Library | none |
| VM Template | the VirtualMachine object of the template, and its Datastore | none |

Notes:

- A template is not a parent of the library item it was cloned to. The API does not store that link. It is not shown.
- A VM Template object is a child of the VirtualMachine object, so the template appears under the VM it describes. It is still a separate object, so it can carry template data without changing the VM object. Whether it should instead replace the VM object is open.
- A subscribed library's item has `source_id`. That is not an inventory object, so no relationship is made. It is a property.

## Properties

Properties are text, published under `vCommunity|`. The VCF Operations names of the VM fields need checking first.

| Object | Properties |
| :--- | :--- |
| Content Library | Name, Library ID, Type (local or subscribed; how to tell them apart is to verify) |
| OVF OVA Template | Name, Type (ovf, ova, or other), Content Version, Stored Locally (`cached`), Security Compliant (`security_compliance`), Certificate Verification (`certificate_verification_info.status`, ovf only), Last Modified, Last Sync (subscribed only), Source Item ID (subscribed only) |
| VM Template | Guest OS, VMware Tools status, Hardware Version, vCPUs, Memory (GB), Disk Used (GB), Encryption, Datastore name, VM folder, Content Library it belongs to (by name, if any), Library Content Version (if any) |

Keys that are not in the item model (for example "Publish state") are not added until seen in a response.

## Metrics

Metrics are numbers, published on the object, and can be charted and alerted on.

| Object | Metric | Meaning |
| :--- | :--- | :--- |
| Content Library | Items | Number of items |
| Content Library | Items Not Stored Locally | Items with `cached` = false |
| Content Library | Items Not Security Compliant | Items with `security_compliance` = false |
| Content Library | Total Size (GB) | Sum of `size` of the items |
| Content Library | Days Since Last Sync | Subscribed libraries only: the oldest item's last sync |
| OVF OVA Template | Size (GB) | `size` / 1 GiB |
| VM Template | Disk Used (GB) | Disk space of the template VM |
| Datastore (existing object) | Template Storage (GB) | Total of the disk space of the VM templates on the datastore |

A template VM has no performance statistics (it cannot run), so no KPI is proposed for it.

## Efficiency

- **VM Template: no new call.** `summary|config|isTemplate` is added to the property list that the pack already reads in one batched call for all VMs (`read_vms`). The cost is one object per template.
- **Content library: new calls.** One list call per vCenter for the libraries, then one list call per library for the items. The item fields are fetched by the list call if it returns them, otherwise by one get call per item. In the lab, `cl-vks01` alone has 138 items, so per-item calls would be 138 requests per cycle. Avoid this.
- **Read on a long window.** Libraries change rarely. Read them at most once per hour, like the Periodic Cluster Check, and keep the last values between reads. This is a design choice; it can be changed.
- **Only changed items.** Within a read, fetch an item again only when its `content_version` or `last_modified_time` has changed. The first read after a restart is the only full read.
- **A separate session.** The vSphere Automation API needs its own session. It is not the same as the pyVmomi connection, so it is a second connection to vCenter.

## Verification

Done before any build, with a read-only probe:

1. The property names of one template VM in VCF Operations, from its properties list.
2. Whether a library item list call returns `cached`, `size`, `security_compliance` and `content_version`, for one library.
3. The item types of the lab's libraries.

Done with a build on the test instance, after an approved install:

4. Whether a pack-created object of its own kind shows in VCF Operations with its parent link to a VirtualMachine or Datastore object.
5. Whether a pack-created object survives a collection cycle, and what happens to an object the pack stops reporting. The Tier probe answers the first half for the related case of another kind's object.

## Open decisions

1. **Read the content libraries from vCenter?** Needs approval; see [Decision needed first](#decision-needed-first).
2. **VM Template: a separate object or a replacement?** Separate, as a child of the VM, is the proposal here. The alternative is to show the template data as properties on the existing VM object.
3. **Which item types?** `ovf`, `ova`, `vm-template`, `iso`, or all.
4. **Subscribed libraries:** include `Days Since Last Sync` now, or later?
5. **Planned work and `docs/`.** [CONTRIBUTING.md](../../CONTRIBUTING.md#documentation) says planned work goes in a GitHub issue, not in `docs/`. This page is in `docs/` because it was asked for. Whether an issue should also be opened is open.

## Not in this design

Alerts and events for templates and libraries.
