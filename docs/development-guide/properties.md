# Properties

A property is a setting of an object, such as the HA settings of a cluster or the license expiry of a host. The pack publishes them under `vCommunity|` on the vCenter objects. This page explains how the code reads and publishes them. For the list of every property, see [Metrics and Properties](../reference/metrics-and-properties.md).

Code: [`Management Pack/app/properties/`](../../Management%20Pack/app/properties/)

## Properties and metrics

| | Property | Metric |
| :--- | :--- | :--- |
| What it is | A setting or an identifier. Text, or a number that is not charted over time. | A number over time, with a value at each collection. |
| Stored | When it changes. VCF Operations keeps the last value. | At every collection, or once per period for the Periodic Cluster Check. |
| Stale value | Kept. The last known value is still true, because it is only stored when it changes. | Left blank after the stale limit (10 minutes), so no old value is shown as current. |

A property is therefore a fact that holds until it changes, and a metric is a reading. The stale rule applies only to metrics, see [Metrics Code](metrics-code.md).

## What is in this folder

| Folder | Module | What it publishes |
| :--- | :--- | :--- |
| `cluster/` | `ha_properties.py` | HA settings of the cluster. |
| `cluster/` | `drs_properties.py` | DRS settings of the cluster. |
| `cluster/` | `dpm_properties.py` | DPM settings of the cluster. |
| `cluster/` | `evc_properties.py` | The EVC mode of the cluster. |
| `cluster/` | `cluster_configuration_properties.py` | Other cluster configuration, such as its status. |
| `host/` | `host_advanced_settings.py` | The ESXi advanced system settings chosen in the configuration file. This is the core of the pack. |
| `host/` | `host_configurations.py` | Host configuration values. |
| `host/` | `host_install_date.py` | When the host was installed. |
| `host/` | `host_licensing.py` | The license assigned to the host, and its expiry. |
| `host/` | `host_software_packages.py` | The software packages (VIBs), by name, version and vendor, as chosen in the configuration file. |
| `host/` | `host_uplink.py` | The uplinks (physical NICs) of the host. |
| `datastore/` | `collect_ds_identifiers_properties.py` | Identifiers of the datastore. |
| `datastore/` | `collect_ds_summary_properties.py` | Summary properties of the datastore. |
| `vcenter/` | `collect_vcenter_properties.py` | Properties of the vCenter, from its settings. |
| `vcenter/` | `certificate.py` | The vCenter certificate: its thumbprint, its status and the previous thumbprint, for the Trust on First Use check. See [TLS and Security Settings](../configuration-guide/tls-and-security.md). |
| `vm/` | `vm_extra_config.py` | The VM advanced parameters (`.vmx` settings) chosen in the configuration file. |
| `vm/` | `vmConfig.py` | Configuration values of the VM, from its configuration file. |
| `vm/` | `vm_configurations.py` | Other VM configuration values. |
| `vm/` | `vm_disk.py` | The disks of the VM. |
| `vm/` | `vmOSInformation.py` | The guest OS of the VM, read inside a Windows guest with `getWindowsOSInformation.ps1`. |
| `vm/` | `vmService.py` | The Windows services of the VM, read inside the guest with `getWindowsServices.ps1`, for the services chosen in the configuration file. |
| `vm/` | `vm_shares.py` | The share per vCPU and per MB of memory, normalised by the size of the VM. |

The modules take the vSphere properties that the collector has already read. Some of them, such as `vmOSInformation.py`, also run a script inside the guest. The scripts are the `.ps1` files in the same folder.

## How a property is published

1. The collector reads the vSphere properties of the objects in one call. See [Collectors](collectors.md#the-pattern).
2. Each property module takes the properties of one object, and sets its values with `with_property()`.
3. Where the value comes from a configuration file, such as the list of advanced settings to read, the file is read once per cycle by `adapter.py` and passed to the modules. Changing the file changes what is published from the next cycle. See [Customization](../configuration-guide/customization.md).

The reading code returns property values as text, as VCF Operations stores most of them. A number that has to be charted over time is published as a metric instead.

## Limitations

- **A property is only as current as its last change.** If a stored property is wrong because its source changed outside the collection, it stays wrong until the next change.
- **Windows guest properties need VMware Tools and a credential**, and depend on the guest being reachable. Without them, the property is missing for that VM, and nothing is published in its place.
- **The configuration files decide what is collected.** A setting that is not in a file is not read, whatever the code can read. See [Content Folder](content-folder.md).
- **Guest scripts run inside the VM.** They are sent to the guest through the vSphere Guest API, and their inputs are checked first, see [Supporting Code](supporting-code.md#utilsguest_argspy).
