# Collectors

A collector gathers the data for one VCF Operations object type, and publishes it. There is one collector per object type. They are called in parallel by `collect` in [`adapter.py`](../../Management%20Pack/app/adapter.py), see [App Folder](app-folder.md).

Code: [`Management Pack/app/collectors/`](../../Management%20Pack/app/collectors/)

## What each collector does

| Collector | VCF Operations object | What it publishes |
| :--- | :--- | :--- |
| `cluster/collectClusterData.py` | Cluster | Cluster properties: HA, DRS, DPM, EVC and configuration. Metrics: DRS Score, Cluster Performance, Cluster Risk, Cluster Consumption, Cluster Operational Availability and the Periodic Cluster Check. |
| `host/collectHostData.py` | ESXi host | Host properties: advanced settings, configuration, install date, licensing, software packages (VIBs) and uplinks. Metrics: ESXi Performance, ESXi Host Operational Availability and Network Speed Degradation. |
| `vm/collectVMData.py` | Virtual machine | VM properties: configuration, extra configuration, disks, OS information, Windows services and shares. Metrics: VM Performance, Guest OS Performance and VM Guest OS. Also the Windows event logs, see [Supporting Code](supporting-code.md#events). |
| `datastore/collectDatastoreData.py` | Datastore | Datastore identifiers and summary properties. |
| `vcenter/collectvCenterData.py` | vCenter | vCenter properties and the certificate check. Worst Cluster Operational Availability, and the Network Speed count of the vCenter. |
| `datacenter/collectDatacenterData.py` | Datacenter | Total Network Speed Degradation: the number of its hosts below 100 %. |
| `world/collectWorldData.py` | vSphere World | The summary metrics over all vCenters: Bottom 10 Percent and worst cluster scores, the top 10 percent and highest cluster utilization, the availability and network counts, and the Cluster Delta Close and Open Counts. |

The metrics and properties themselves are in [Metrics Code](metrics-code.md) and [Properties](properties.md). A collector does not calculate them. It finds the objects, reads their inputs and calls the modules.

## The pattern

Every collector follows the same steps:

1. Read the vSphere properties of the objects, in one call for all objects of the type, through [`utils/vi_property_collector.py`](../../Management%20Pack/app/utils/vi_property_collector.py). Only the properties listed are read, so the call stays small.
2. Find the matching VCF Operations object. The vSphere object is matched to it by its MoRef id, the `VMEntityObjectID` identifier. An object that is not found in VCF Operations is skipped.
3. Read the stats the modules need, once for the whole vCenter, before the loop over the objects. Stats are read in batches, see [Supporting Code](supporting-code.md#utilsops_statspy).
4. For each object, call the property and metric modules, and add the object to the result with `result.add_object()`.

A failure on one object is logged as a warning and the loop goes on with the next. A failure in the whole collector is caught in `adapter.py`, so the other collectors still publish.

## Why one collector per object type

- VCF Operations stores each metric and property on one object type. A collector that works on one type of object is the simplest way to put a value on the right object.
- The vSphere properties and the VCF Operations stats of one type can be read together, once, instead of once per object.
- A new object type is one new folder, with one collector and one call in `adapter.py`.

## Limitations

- **A collector publishes only the objects that VCF Operations already knows.** The objects are created by the vCenter adapter. A new vSphere object appears in the pack's metrics only after the vCenter adapter has collected it.
- **The vSphere World collector runs in every account.** There is one vSphere World object for all vCenters, so every account publishes the same values for it. See [vSphere World](../reference/metrics/vsphere-world-metrics.md).
- **Stats are read from VCF Operations, not from vCenter.** A value is therefore as old as the last collection of the vCenter adapter, and a stat older than the stale limit is no data.
- **The Windows checks depend on the guest.** Properties and event logs of a VM need VMware Tools and a credential. Without them, those properties and events are missing for that VM. See [TLS and Security Settings](../configuration-guide/tls-and-security.md).
