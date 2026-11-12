# Supporting Code

The modules that the collectors, metrics and properties share: `utils/` for reading data, connections, guest operations and collection health, `constants/` for shared names, and `events/` for the Windows event logs. Apart from `collection_health.py` and the events module, none of them publishes anything on its own.

Code: [`Management Pack/app/utils/`](../../Management%20Pack/app/utils/), [`constants/`](../../Management%20Pack/app/constants/), [`events/`](../../Management%20Pack/app/events/)

## utils/

### utils/ops_stats.py

Reads what VCF Operations already holds: resources, stats, properties and relationships. The vCenter adapter of VCF Operations collects most of the inputs the KPIs need, so the pack reads them back through the Suite API instead of collecting them from vCenter a second time.

| Function | Returns |
| :--- | :--- |
| `query_resources()` | The resources of one kind, under one adapter instance or all of them, with the VCF Operations id that the other calls need. The SDK's own query does not return this id. |
| `read_latest_stats()` | The latest value of each stat. A value older than the stale limit (10 minutes) counts as no data. The optional `max_age_minutes` is used only for the port group count on vSphere World, with `CONFIGURATION_STALE_AFTER_MINUTES` (15 minutes). See [the two limits](../reference/metrics/README.md#two-limits-10-minutes-and-15-minutes-for-settings-based-metrics). |
| `read_latest_instance_stats()` | The latest value of each instance of a stat, such as `net:vmnic0|speed` for one NIC. |
| `read_latest_timestamps()` | When each stat was last written, however old. Returns `None` if a request fails, so the caller can't mistake "not read" for "never published". |
| `read_stat_history()` | The 5-minute samples of a time range, for the Periodic Cluster Check. The ids whose request failed are added to the caller's `failed` list. |
| `read_latest_properties()` | The latest value of each property, as text. `as_number()` converts a value to a number. |
| `read_related()` | The parents or children of one resource. Raises if the request fails, so the caller publishes nothing rather than a value built on part of the objects. |

The latest-value queries take up to 1,000 resources per request, so a large vCenter needs only a few requests per cycle. History requests hold fewer resources, because each stat returns many samples. Relationship reads are one request per object: the Business Application job reads one per Tier, application, child and Enterprise, and the resource pool count reads one per pool.

**Limitations:**

- When one batch of `read_latest_stats()` or `read_latest_properties()` fails, the function logs a warning and returns the other batches. The resources of the failed batch are missing from the result, so a caller that sums or averages can publish a total built on part of the objects ([issue #60](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/60)).
- The data is what VCF Operations holds. A stat that the vCenter adapter has not collected is not available, whatever the pack's settings.

### utils/ops_inventory.py

Reads from VCF Operations which hosts are in each cluster, which powered-on VMs run on each host, the VM sizes, the host cores and threads, and the host connection, maintenance and power state. `read_cluster_ha()` reads each cluster's host count and HA failover level, for Operational Availability. The KPIs need this placement to score clusters and hosts. It is read once per cycle, for all clusters.

**Limitations:**

- The placement is what VCF Operations held at the vCenter adapter's last collection, so it can be up to a cycle old.
- Placement is matched by name: a VM's `summary|parentHost` and a host's `summary|parentCluster` hold names, not ids. Names are unique within a datacenter.

### utils/vi_property_collector.py

Reads a list of properties from all vSphere objects of one type through the vSphere PropertyCollector, using a container view. The results come back in pages of 100 objects. The view is released after the read, so threads that share the connection don't share views.

**Limitations:**

- A slow vCenter slows the whole cycle, because every collector reads through the same connection.
- An invalid property path raises `InvalidProperty`. It is logged and raised again, so the whole read fails. This matters for `vm_options.xml`, whose entries are property paths: one misspelt path stops the VM collection for the cycle. See [Configuration files](../troubleshooting-guide/configuration-files.md).

The vCenter collector reads its settings with `OptionManager.QueryOptions`, one call per setting, and the port group count makes its own reads.

### utils/config_files.py

Reads the configuration files of an Adapter Instance, the lists of settings the pack collects. A file is an XML document whose text is a comma-separated list. `parse_list()` turns the text into a list, and `check_xml()` checks the Windows event list, which is passed to the guest as it is.

A file that is missing, unreadable or not valid XML gives an empty list for that file only. The rest of the cycle is collected, and the problem text (`missing_problem()`, `unreadable_problem()`, `invalid_problem()`) is published as an event on the vCenter object. See [Configuration files](../troubleshooting-guide/configuration-files.md).

**Limitations:** the module checks that the file is valid XML. It can't tell whether a name in the list is a real setting. A misspelt ESXi setting, VM parameter or package name is not collected, and at most shows as a warning in the adapter log.

### utils/tls.py

Turns the TLS settings of the Adapter Instance into connection arguments, so the collectors don't handle certificates themselves. The modes are described in [TLS and Security Settings](../configuration-guide/tls-and-security.md).

| Function or class | Purpose |
| :--- | :--- |
| `vcenter_mode()`, `vcenter_connect_args()` | The pyVmomi connection arguments for the vCenter TLS Validation mode. |
| `normalize_thumbprint()` | Checks a thumbprint that someone typed, and normalises it. |
| `presented_thumbprint()` | Reads the certificate vCenter presents, in a TLS handshake that sends no credentials. Used every cycle for the Trust on First Use check. |
| `PinnedAdapter` | A `requests` adapter that checks the certificate fingerprint during the handshake. Used by the REST session for content libraries in `Pinned` mode. |
| `explain_connect_error()` | Turns a failed connection into a message that says what to change. |

### utils/guest_http.py

The HTTPS file transfers of the vSphere Guest API, which copy a script into a Windows VM and read its output back. The transfer goes to the ESXi host that runs the VM, and the host certificate is checked against the thumbprint vCenter records for the host:

- `Pinned` (default): a different certificate is refused. When vCenter has no thumbprint for the host, the transfer goes ahead unchecked, with one warning per host.
- `Strict`: a host with no thumbprint in vCenter is refused too.
- `Disabled`: no check.

The mode, the thumbprints read from vCenter and the hosts already warned about are module state, shared by the threads and guarded by a lock. `configure()` sets the mode and clears the rest at the start of each cycle, so a replaced ESXi certificate is picked up in the next cycle.

### utils/guest_ops.py

The Guest API steps that the three Windows guest collectors share: `transfer_file`, `run_powershell`, `file_exists`, `read_guest_output`, `create_temp_file` and `remove_temp_dir`. Each collector (`properties/vm/vmService.py`, `properties/vm/vmOSInformation.py`, `events/vm/collect_windows_event_logs.py`) keeps only its own parsing and publishing.

- `run_powershell` polls for the script to finish, backing off from 1 to 10 seconds. After 5 minutes it stops the process and raises `GuestProcessTimeout`. The VM is skipped for the cycle, and no other VM waits for it.
- `read_guest_output` returns `None` when the download fails. The caller checks for it, so a failed download is never read as an empty file.
- `GuestBudget` limits the guest work of one cycle to 30 minutes. The VM collector checks it before the guest steps of each VM.

### utils/guest_args.py

Values from the configuration files end up in PowerShell commands that run inside a Windows guest, so this module checks them first. For example, `safe_service_names()` keeps only service names that are safe to put in a command line. People edit the configuration files, so their values are never trusted as code.

### utils/collection_health.py

Counts the warnings and errors of one cycle, and publishes the result on the vCenter object:

- `start()` adds a logging handler to the root logger at the start of the cycle. It counts every `WARNING` and `ERROR` record, and keeps the first message, cut to 250 characters.
- `publish()` sets `vCommunity|Collection Health|Warnings in Last Cycle` (a metric) and `vCommunity|Collection Health|First Warning` (a property) on the vCenter object. A clean cycle publishes 0 and `None in the last cycle`.
- `stop()` removes the handler.

The alert **vCommunity Collection Warnings** ([`content/alertdefs/Collection Warnings.xml`](../../Management%20Pack/content/alertdefs/Collection%20Warnings.xml)) fires when the count is above zero. Like the pack's other alerts, it ships deactivated in the base policy. The pack catches most failures and publishes the rest of the cycle, so without this count a missing value would only show in the log. See [Symptoms](../troubleshooting-guide/symptoms.md#a-collection-warnings-alert-is-shown).

## constants/

`constants/main.py` holds the names used across the pack:

| Name | Value | Meaning |
| :--- | :--- | :--- |
| `ADAPTER_KIND` | `vCommunity` | The adapter kind of this pack in VCF Operations. |
| `ADAPTER_NAME` | `VCF vCommunity Adapter` | The name of the adapter kind as the UI shows it. |
| `VCENTER_ADAPTER_KIND` | `VMWARE` | The adapter kind of the vCenter adapter, whose objects the pack reads and adds to. |
| `HOST_IDENTIFIER`, `PORT_IDENTIFIER` | `host`, `port` | The Adapter Instance identifiers: the vCenter address and port. |
| `USER_CREDENTIAL`, `PASSWORD_CREDENTIAL` | `user`, `password` | The credential fields of the Adapter Instance. |
| `VCENTER_TLS_VALIDATION`, `VCENTER_THUMBPRINT`, `GUEST_TLS_VALIDATION` | | The TLS settings. See `utils/tls.py`. |

`constants/cluster/`, `constants/host/` and `constants/vm/` are empty packages reserved for names of those object types. Nothing imports them yet. Add a name there when a second module needs it.

## events/

`events/vm/collect_windows_event_logs.py` reads the Windows event logs of a VM. It copies `getWindowsEventLogs.ps1` and an XML file with the Event IDs into the guest through the Guest API, runs the script, reads the CSV it writes, and publishes the events it finds on the VM in VCF Operations. At most 100 events per VM are published per cycle (`MAX_EVENTS_PER_VM`). The Event IDs come from the configuration file named on the Adapter Instance, `windows_event_list.xml` by default. See [Content Folder](content-folder.md).

**Limitations:**

- It needs VMware Tools in the VM, a Windows credential, and **Windows Event Log Monitoring Status** set to `Enabled`. Without them, no event is collected for that VM.
- The script runs in the guest, so a slow or busy VM takes longer. The run is part of the VM collection and adds to the cycle time, within the 30-minute guest budget.
