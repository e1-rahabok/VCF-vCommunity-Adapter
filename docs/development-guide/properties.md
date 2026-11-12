# Properties

A property is a setting or an identifier of an object, such as the HA settings of a cluster or the license expiry of a host. The pack publishes its properties under `vCommunity|`. This page describes how the code reads and publishes them. Every property is listed in [Metrics and Properties](../reference/metrics-and-properties.md).

Code: [`Management Pack/app/properties/`](../../Management%20Pack/app/properties/)

## Properties and metrics

| | Property | Metric |
| :--- | :--- | :--- |
| What it is | A setting or an identifier. Text, or a number that is not charted over time. | A number over time, with a value at each collection. |
| Stored | When it changes. VCF Operations keeps the last value. | At every collection, or once per period for the Periodic Cluster Check. |
| After the source stops reporting | The last value stays. VCF Operations stores a property only when it changes, so its last value is its current value. | Left blank after the stale limit (10 minutes), so an old value is not shown as current. |

The stale limit applies only to metrics. See [Metrics Code](metrics-code.md).

## What is in this folder

| Folder | Module | What it publishes |
| :--- | :--- | :--- |
| `cluster/` | `ha_properties.py` | The HA settings of the cluster. |
| `cluster/` | `drs_properties.py` | The DRS settings of the cluster. |
| `cluster/` | `dpm_properties.py` | The DPM settings of the cluster. |
| `cluster/` | `evc_properties.py` | The EVC mode of the cluster. |
| `cluster/` | `cluster_configuration_properties.py` | Other cluster configuration, such as its status. |
| `host/` | `host_advanced_settings.py` | The ESXi advanced system settings listed in the configuration file. |
| `host/` | `host_configurations.py` | Host configuration values. |
| `host/` | `host_install_date.py` | When the host was installed. |
| `host/` | `host_licensing.py` | The licenses assigned to the host, and their expiry. |
| `host/` | `host_software_packages.py` | The software packages (VIBs) listed in the configuration file, with name, version and vendor. |
| `host/` | `host_uplink.py` | The uplinks (physical NICs) of the host. |
| `datastore/` | `collect_ds_identifiers_properties.py` | Identifiers of the datastore. |
| `datastore/` | `collect_ds_summary_properties.py` | Summary properties of the datastore. |
| `vcenter/` | `collect_vcenter_properties.py` | vCenter settings, such as event and task retention and database connections. |
| `vcenter/` | `certificate.py` | The vCenter certificate for the Trust on First Use check: the thumbprint, the status and the previous thumbprint. It reads the recorded thumbprint back from VCF Operations each cycle. See [TLS and Security Settings](../configuration-guide/tls-and-security.md). |
| `vm/` | `vm_extra_config.py` | The VM advanced parameters (`.vmx` settings) listed in the configuration file. |
| `vm/` | `vmConfig.py` | The VM options: the vSphere property paths listed in `vm_options.xml`. |
| `vm/` | `vm_configurations.py` | Other VM configuration values, such as boot options, firmware, NUMA, VMware Tools settings and the hardware upgrade policy. |
| `vm/` | `vm_disk.py` | The disks and SCSI controllers of the VM. |
| `vm/` | `vmOSInformation.py` | The guest OS, read inside a Windows guest with `getWindowsOSInformation.ps1`. Runs only when Guest OS Service Monitoring is enabled. |
| `vm/` | `vmService.py` | The Windows services listed in the configuration file, read inside the guest with `getWindowsServices.ps1`. |
| `vm/` | `vm_shares.py` | The share per vCPU and per MB of memory, normalised by the size of the VM. Published as metrics for now, although they should be properties ([issue #49](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/49)). |

Some properties are published outside this folder:

| Property | Published by |
| :--- | :--- |
| Content Library, Library Item and VM Template properties | `collectors/library/`. See [Template and Content Library Design](template-and-library-design.md). |
| vCenter Patch Level | `collectors/vcenter/collectvCenterData.py` |
| Collection Health First Warning, on the vCenter object | `utils/collection_health.py`. See [Supporting Code](supporting-code.md#utilscollection_healthpy). |

Most modules work on the vSphere properties that the collector has already read. The Windows modules also run a script inside the guest. The scripts are the `.ps1` files in the same folder.

## How a property is published

1. The collector reads the vSphere properties of all objects of a type in one paged read. See [Collectors](collectors.md#the-pattern).
2. Each property module takes the properties of one object and sets its values with `with_property()`.
3. Where a configuration file decides what to read, such as the list of advanced settings, `adapter.py` reads the file once per cycle and passes the list to the modules. A change to the file takes effect from the next cycle. See [Customization](../configuration-guide/customization.md).

Property values are published as text, as VCF Operations stores most properties. A number that should be charted over time is published as a metric instead.

## Limitations

- **A property is as current as its last change.** A host that the host collector skips, for example because it is disconnected, keeps its last values.
- **Windows guest properties need VMware Tools, a Windows credential and a reachable guest.** Without them the property is missing for that VM, and nothing is published in its place.
- **The configuration files decide what is collected.** A setting that is not listed in a file is not read, even if the code could read it. The shipped ESXi, VM and Windows service files list nothing, so their properties appear only after you list settings in a file. See [Content Folder](content-folder.md).
- **Guest scripts run inside the VM.** They are sent through the vSphere Guest API, and their inputs from the configuration files are checked first. See [Supporting Code](supporting-code.md#utilsguest_argspy).
