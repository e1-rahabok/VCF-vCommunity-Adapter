# Template and Content Library Design

The design record of the three object types the pack creates for templates and content libraries: **Content Library**, **Library Item** and **VM Template**. The model behind them is in [Templates and Content Libraries](../concepts/templates-and-content-libraries.md). The keys are listed in [Metrics and Properties](../reference/metrics-and-properties.md).

**Status:** built and shipped since 0.6.6. The Content Library to Library Item links were checked on the test instance with 0.7.3. The VM Template objects have no live check yet, and the [live validation](../../tools/validate/validate.md) does not check any of the three object types. The parts that are not built are listed under [Not built](#not-built).

Code: [`collectors/library/collectLibraryData.py`](../../Management%20Pack/app/collectors/library/collectLibraryData.py), [`collectors/library/collectTemplateData.py`](../../Management%20Pack/app/collectors/library/collectTemplateData.py). Tests: `tests/test_library_collection.py`, `tests/test_vm_template.py`.

## Object types

The pack creates all three under its own adapter kind, `vCommunity`, with `define_object_type` in `definition.py`. It does not change the vCenter adapter's objects.

| Object type | Created from | Name | Identifiers |
| :--- | :--- | :--- | :--- |
| `Content Library` | The vSphere Automation REST API, one object per library | The library name | `Library ID` |
| `Library Item` | The vSphere Automation REST API, one object per item of every library, of every type | The item name | `Item ID` |
| `VM Template` | The VM collector's vSphere read, one object per VM whose `config.template` is true | The VM name | `VMEntityObjectID`, `VMEntityVCID` |

## Decisions

- **Read content libraries through the vSphere Automation REST API** (approved on 2026-10-28). The vCenter adapter of VCF Operations has no content library or library item objects, and pyVmomi does not cover content libraries. This adds a second connection to vCenter, next to the pyVmomi connection, with the same account.
- **One object type for all library items**, with `Type` as a property. It covers `ovf`, `ova`, `vm-template`, `iso`, `other` and any type added later. Limiting the object type to OVF and OVA would hide the other items, and a property costs nothing.
- **Build VM Template from the VM collector's read.** The template flag is the vSphere property `config.template`. The paths the template needs are added to the VM collector's PropertyCollector read (`PROPERTY_PATHS` in `collectTemplateData.py`), so there is no separate read of all VMs. VCF Operations already shows a template as a VirtualMachine, but it has no template object type of its own.
- **Publish every defined key, every cycle.** A value that the API does not return is published as an empty string, so the object always has the same set of keys.
- **No parent links to objects outside the result.** See below.

## Parent and child relationships

| Object | Parent | Children |
| :--- | :--- | :--- |
| `Content Library` | none | its `Library Item` objects |
| `Library Item` | its `Content Library` | none |
| `VM Template` | none | none |

- **The pack sends its relationships in `PER_OBJECT` mode** (`result.update_relationships` in `adapter.py`). In this mode only the objects in the result have their child lists replaced. The vCenter object and the VM folders are not in the result, so the pack can't add a child to them without replacing their other children. For this reason the Content Library → vCenter and VM Template → VM folder links are not written. Versions 0.6.6 to 0.7.2 wrote them in the default mode, so links from those versions may still exist on an instance. This has not been checked.
- **Why not the default mode.** With the default (`AUTO`), any relationship in the result makes VCF Operations remove every relationship that is not in the result, including the manual members of Business Applications. See [Business Application Performance](../reference/metrics/business-application-performance.md#membership-is-kept).
- **Library Item and VM Template are not linked.** A library item has no field in the API that names the inventory template it came from.
- **Subscriptions are properties, not links.** A subscribed library points to a published library through its subscription URL, and a subscribed item points to its source through `source_id`. The published library is not an object in VCF Operations, so both are kept as properties.
- **A VM's template is not known.** One template has many VMs, and a VM has at most one template, but neither vSphere nor VCF Operations stores the link. See [Still open](#still-open).

## Properties and metrics

All keys are under `vCommunity|<object type>|`.

| Object | Properties | Metrics |
| :--- | :--- | :--- |
| `Content Library` | Type (the API value, local or subscribed), Subscription URL, Automatic Sync, State | Items, Items Not Stored Locally, Items Not Security Compliant, Total Size (GB) |
| `Library Item` | Type, Description, Version, Content Version, Stored Locally (`cached`), Security Compliant (`security_compliance`), Certificate Verification (`certificate_verification_info.status`), Last Modified, Last Sync, Source Item ID (`source_id`) | Size (GB) |
| `VM Template` | Guest OS, Hardware Version, vCPUs, Memory (GB), Datastore, VM Folder | Disk Used (GB) |

- Items Not Stored Locally and Items Not Security Compliant count the items where the field is false or missing.
- Sizes are in GiB, rounded to two decimals.
- A template can't run, so it has no performance statistics and no KPI.

## Efficiency

- **VM Template:** the template paths ride on the VM collector's batched read. The folder name and the datastore names are then read from the VM's managed objects, which costs a few small calls per template.
- **Content libraries: one request per item.** The item list returns only item IDs, so each item needs its own GET to read its size, state and compliance. Per library there is one GET for the library and one for its item list. This can't be avoided while those fields are needed.
- **Every cycle.** The libraries are read in every collection cycle, with a login and a logout. Each cycle runs in a new process, so nothing is kept between cycles. Reading less often would need state that survives the process, which the pack does not have. For a large library this is the cost to watch. A longer interval, or a cheap check for changes, is on the [To Do project](https://github.com/users/e1-rahabok/projects/1). It needs one full read measured first.

## TLS for the REST connection

The REST session follows the **vCenter TLS Validation** setting of the Adapter Instance (`verify_for()` in `collectLibraryData.py`):

| Mode | REST connection |
| :--- | :--- |
| `Enabled` | The certificate is checked against the Cloud Proxy's trust store. |
| `Pinned` | The certificate must match the SHA-256 thumbprint, checked during the TLS handshake before the login (`tls.PinnedAdapter`). A thumbprint that is not SHA-256 stops the library read. |
| `Trust on First Use` | Not checked, as for the pyVmomi connection. The certificate is watched separately on the vCenter object. |

A failure in the library read is logged as a warning and publishes no library objects for the cycle. The rest of the collection goes on. See [TLS and Security Settings](../configuration-guide/tls-and-security.md).

## Still open

**What links a VM to its template?** VCF Operations does not store the link, so the pack needs another source. The options are:

- **vCenter task history.** A clone task records its source template. This is a new read from vCenter beyond the library read, so it needs approval first. How long vCenter keeps task history must be checked.
- **A VM annotation or custom attribute** set by the tool that provisions the VM. This works only for VMs made by that tool.

Until one is chosen, VM Template objects have no children.

## Not built

- The VMs of a template, as children of the VM Template, and its Number of VMs metric.
- Template Storage (GB) on the Datastore: the disk space of the VM templates on it.
- A sync-age metric for subscribed libraries. It is on the [To Do project](https://github.com/users/e1-rahabok/projects/1).
- Alerts and events for templates and libraries.
