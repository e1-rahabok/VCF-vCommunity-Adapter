# Collectors

A collector gathers the data for one object type and publishes it. Most collectors match one object type of the vCenter adapter. Two more build the pack's own object types for content libraries and templates. `_run_object_jobs()` in [`adapter.py`](../../Management%20Pack/app/adapter.py) runs them in parallel, together with the Business Application job. See [App Folder](app-folder.md#one-collection-cycle).

Code: [`Management Pack/app/collectors/`](../../Management%20Pack/app/collectors/)

## What each collector does

| Collector | Object | What it publishes |
| :--- | :--- | :--- |
| `cluster/collectClusterData.py` | Cluster | Properties: HA, DRS, DPM, EVC and cluster configuration. Metrics: DRS Score, Cluster Performance, Cluster Risk, Cluster Consumption, Cluster Operational Availability, Number of Resource Pools and Cascading Resource Pools, and the Periodic Cluster Check. |
| `host/collectHostData.py` | ESXi host | Properties: advanced settings, configuration, install date, licensing, software packages (VIBs) and uplinks. Metrics: ESXi Performance, ESXi Host Operational Availability and Network Speed Degradation. |
| `vm/collectVMData.py` | Virtual machine | Properties: configuration, VM options, advanced parameters, disks, and, with Windows monitoring, OS information and Windows services. Metrics: VM Performance, Guest OS Performance, VM Guest OS, and Share per vCPU and per MB. Events: Windows event logs, see [Supporting Code](supporting-code.md#events). It also calls the VM Template collector for each template. |
| `datastore/collectDatastoreData.py` | Datastore | Identifier and summary properties. |
| `vcenter/collectvCenterData.py` | vCenter | Properties: vCenter settings, Patch Level, and the certificate check. Metrics: Worst Cluster Operational Availability and Number of Port Groups. Events: one `vCommunity configuration:` event per configuration file problem. |
| `datacenter/collectDatacenterData.py` | Datacenter | Total Network Speed Degradation: the number of its hosts below 100 %. |
| `world/collectWorldData.py` | vSphere World | Summaries over all vCenters: worst and Worst 10 Percent Cluster Performance and Cluster Risk, highest and Highest 10 Percent Cluster Utilization, availability summaries, Total Network Speed Degradation, Cluster Delta Close and Open Counts, Number of Port Groups, and the VMware Tools counts. |
| `library/collectLibraryData.py` | Content Library, Library Item (pack objects) | Library and item properties and metrics, read from the vSphere Automation REST API. See [Template and Content Library Design](template-and-library-design.md). |
| `library/collectTemplateData.py` | VM Template (pack object) | Template properties and Disk Used, from the VM collector's read. Called by the VM collector, not by `adapter.py`. |

The Business Application job is not in this folder. It is [`metrics/container/business_app_performance.py`](../../Management%20Pack/app/metrics/container/business_app_performance.py), which reads the Container objects (Tier, BusinessService and Enterprise) and their relationships from VCF Operations. See [Business Application Performance](../reference/metrics/business-application-performance.md).

The collection health metric and property on the vCenter object are published by `adapter.py` at the end of the cycle, not by the vCenter collector. See [Supporting Code](supporting-code.md#utilscollection_healthpy).

A collector does not calculate metrics or format properties itself. It finds the objects, reads their inputs and calls the modules described in [Metrics Code](metrics-code.md) and [Properties](properties.md).

## The pattern

The cluster, host, VM and datastore collectors follow the same steps:

1. Read the vSphere properties of all objects of the type through [`utils/vi_property_collector.py`](../../Management%20Pack/app/utils/vi_property_collector.py). Only the listed properties are read, and the results come back in pages of 100 objects.
2. Find the matching VCF Operations object by its MoRef id, the `VMEntityObjectID` identifier. An object that VCF Operations doesn't have is skipped.
3. Read the stats the modules need from VCF Operations, in batches, before the loop over the objects. See [Supporting Code](supporting-code.md#utilsops_statspy).
4. For each object, call the property and metric modules, and add the object to the result with `result.add_object()`.

A failure on one object is logged as a warning, and the loop continues with the next object. A failure of the whole collector is caught and logged in `adapter.py`, so the other jobs still publish.

The other jobs differ:

- **vCenter** finds its object by the vCenter's instance UUID, and reads its settings one by one with `OptionManager.QueryOptions`.
- **vSphere World and Datacenter** read only from VCF Operations, not from vSphere.
- **Content libraries** read from the vSphere Automation REST API with their own session.
- **VM Template** reuses the VM collector's read.
- **Business Applications** read the Container objects and their relationships from VCF Operations.

## Why one collector per object type

- VCF Operations stores each metric and property on one object type. A collector that handles one type puts each value on the right object.
- The vSphere properties and the VCF Operations stats of one type can be read together, once, instead of once per object.
- A new object type is one new folder, with one collector and one job in `adapter.py`.

## Limitations

- **Most collectors publish only objects that VCF Operations already has.** The vCenter adapter creates those objects, so a new vSphere object gets the pack's values only after the vCenter adapter has collected it. The content library and template collectors are the exception: they create their own objects.
- **Hosts that are not connected are skipped.** The host collector publishes nothing for a host that vCenter does not report as connected. That host keeps the last values it had.
- **The vSphere World and Business Application jobs run in every Adapter Instance.** There is one vSphere World object for all vCenters, and the Business Application objects are read under every adapter instance, so every Adapter Instance publishes the same values for them. See [vSphere World](../reference/metrics/vsphere-world-metrics.md).
- **Stats come from VCF Operations, not from vCenter.** A value is as old as the last collection of the vCenter adapter, and a stat older than the stale limit counts as no data.
- **Windows checks depend on the guest.** The OS information, services and event logs of a VM need VMware Tools, a Windows credential and the monitoring switch on the Adapter Instance. OS information is read only when Guest OS Service Monitoring is enabled. See [TLS and Security Settings](../configuration-guide/tls-and-security.md).
