# Supporting Code

The folders that the collectors, metrics and properties use: `utils/` for reading and for connections, `constants/` for names, and `events/` for the Windows event logs. None of them publishes a metric by itself.

Code: [`Management Pack/app/utils/`](../../Management%20Pack/app/utils/), [`constants/`](../../Management%20Pack/app/constants/), [`events/`](../../Management%20Pack/app/events/)

## utils/

### utils/ops_stats.py

Reads what VCF Operations already holds: the resources, their stats and their properties. The vCenter adapter of VCF Operations collects these. The pack reads them back through the Suite API, so nothing is collected from vCenter twice.

- `query_resources()` returns the resources of one kind, with the VCF Operations id that the other calls need. The SDK's objects do not carry this id.
- `read_latest_stats()` returns the last value of each stat. A value older than the stale limit (10 minutes) is no data. Its optional `max_age_minutes` is used by one metric only: the port group count on vSphere World, with `CONFIGURATION_STALE_AFTER_MINUTES` (15 minutes). See [the two limits](../reference/metrics/README.md#two-limits-10-minutes-and-15-minutes-for-settings-based-metrics).
- `read_latest_timestamps()` returns when each stat was last written, however old. Used to know what was already calculated.
- `read_stat_history()` returns the 5-minute samples of a time range, for the Periodic Cluster Check.
- `read_latest_properties()` returns the last value of each property.

**Why:** the API takes many objects in one request. A request is made per 1,000 resources, so a large vCenter is a few requests per cycle, not thousands.

**Limitations:**

- A request that fails is logged and its objects get no value. Some functions return `None`, so the caller can tell "not read" from "no data". Callers must check for it.
- The data is what VCF Operations holds. A stat the vCenter adapter has not collected is not available, however the pack is configured.

### utils/ops_inventory.py

Reads, from VCF Operations, which hosts are in each cluster, which powered-on VMs run on each host, the VM sizes, and the host cores and threads. The KPIs need this to calculate the cluster and host scores. It is read once per cycle, for all clusters.

**Limitations:** the placement is the one VCF Operations holds at the last collection of the vCenter adapter, so it can be up to a cycle old.

### utils/vi_property_collector.py

Reads a list of properties from many vSphere objects of one type, in one call, through the vSphere PropertyCollector. The collectors use it, so only the properties they need are read.

**Limitations:** the vSphere API is called once per collector per cycle, from the connection that `adapter.py` opened. A slow vCenter makes the whole cycle slow.

### utils/config_files.py

Reads the configuration files of an Adapter Instance: the lists of settings that the pack collects. A file is an XML document whose text is a comma-separated list. The module turns the text into the list, and writes the problem text when a file cannot be used.

**Why:** a bad file must lose only its own data. Before this module, one malformed file failed the whole collection every cycle. Now the file gives an empty list, the rest is collected, and the problem is published as an event on the vCenter object. See [Configuration files](../troubleshooting-guide/configuration-files.md).

**Limitations:** the check is that the file is valid XML and that its text is a list. The module cannot tell whether a name in the list is a real setting, so a misspelt name is not collected, and may only show as a warning in the adapter log.

### utils/tls.py

Turns the TLS setting of the Adapter Instance into the arguments of the vCenter connection, and checks a thumbprint that a person typed. It also explains a failed connection in plain words. The modes and their meaning are in [TLS and Security Settings](../configuration-guide/tls-and-security.md).

**Why:** the choice is made once, here, so the collectors do not handle certificates.

### utils/guest_http.py

The HTTPS calls of the vSphere Guest API file transfers, which copy a script into a Windows VM and run it. The ESXi host certificate is checked, unless the Adapter Instance says otherwise.

### utils/guest_ops.py

The GuestAPI steps that the three Windows guest collectors share: `transfer_file`, `run_powershell`, `file_exists`, `read_guest_output`, `create_temp_file` and `remove_temp_dir`. Each collector (`properties/vm/vmService.py`, `properties/vm/vmOSInformation.py`, `events/vm/collect_windows_event_logs.py`) keeps only its own parsing and its own properties.

- `run_powershell` waits for the script with a poll that backs off from 1 to 10 seconds. After 5 minutes it stops the process, and raises `GuestProcessTimeout`. The VM is then skipped for the cycle, and no other VM waits for it.
- `read_guest_output` returns `None` when the download fails. The caller must check it, so that a failed download is never read as an empty file.
- `GuestBudget` limits the guest work of one cycle to 30 minutes. The VM collector asks it before the guest steps of each VM.

### utils/guest_args.py

Values from the configuration files end up in PowerShell commands run inside a Windows guest. This module checks them first. For example, `safe_service_names()` keeps only the service names that are safe to put in a command.

**Why:** the configuration files are edited by people. Their values must never be trusted as code.

## constants/

`constants/main.py` holds the names used across the pack:

| Name | Value | Meaning |
| :--- | :--- | :--- |
| `ADAPTER_KIND` | `vCommunity` | The adapter kind of this pack in VCF Operations. |
| `VCENTER_ADAPTER_KIND` | `VMWARE` | The adapter kind of the vCenter adapter, whose objects the pack reads and enriches. |
| `HOST_IDENTIFIER`, `PORT_IDENTIFIER` | `host`, `port` | The identifiers of the Adapter Instance: the vCenter address and port. |
| `USER_CREDENTIAL`, `PASSWORD_CREDENTIAL` | `user`, `password` | The credential of the Adapter Instance. |
| `VCENTER_TLS_VALIDATION`, `VCENTER_THUMBPRINT`, `GUEST_TLS_VALIDATION` | | The TLS settings, see `utils/tls.py`. |

`constants/cluster/`, `constants/host/` and `constants/vm/` are empty packages, reserved for the names of those object types. Nothing imports them yet. Add names there when a second module needs the same name, not before.

## events/

`events/vm/collect_windows_event_logs.py` reads the Windows event logs of a VM. It copies `getWindowsEventLogs.ps1` into the guest through the Guest API, runs it, reads the CSV it writes, and publishes the events found in VCF Operations. The events to look for are listed in `content/files/solutionconfig/windows_event_list.xml`. See [Content Folder](content-folder.md).

**Limitations:**

- It needs VMware Tools in the VM and a Windows credential. Without them, no event is collected for that VM.
- The script runs in the guest, so a slow or busy VM takes longer. The run is part of the VM collection, so it adds to the cycle time.
