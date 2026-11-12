# The App Folder

`Management Pack/app/` holds the Python code of the adapter. It is the only part of the repository that runs in VCF Operations. The Dockerfile copies it into the container image that the Cloud Proxy runs, together with `commands.cfg` and `adapter_requirements.txt`.

Code: [`Management Pack/app/`](../../Management%20Pack/app/)

## What the adapter does

The adapter reads the ESXi, VM and cluster data that the vCenter adapter of VCF Operations does not collect, calculates metrics and KPIs from it, and publishes the results under the `vCommunity|` key prefix. It publishes in three places:

- **On the vCenter adapter's objects** (vCenter, Datacenter, Cluster, ESXi host, VM, Datastore and vSphere World). These objects already exist in VCF Operations. The pack adds properties and metrics to them.
- **On the Container objects** that VCF Operations uses for Business Applications: Tier, BusinessService and Enterprise. See [Business Application Performance](../reference/metrics/business-application-performance.md).
- **On its own object types**: Content Library, Library Item and VM Template. See [Template and Content Library Design](template-and-library-design.md).

It publishes three kinds of value:

- **Properties**: settings and identifiers, such as an advanced setting or a license expiry date.
- **Metrics**: numbers over time, such as the Operational Availability of a cluster.
- **KPIs**: a 0 to 100 score built from many sub-metrics. See [Metrics Code](metrics-code.md).

## What is in it

| Path | What it is | Page |
| :--- | :--- | :--- |
| `adapter.py` | The entry point: the `test`, `collect`, `adapter_definition` and `endpoint_urls` methods. | This page |
| `definition.py` | The adapter definition: the object types, groups, metrics, properties and Adapter Instance settings that VCF Operations shows. It also holds `define_kpi()`, which builds a KPI's definition from its table, and `KPI_UNITS`. | [Metrics Code](metrics-code.md) |
| `collectors/` | One collector per object type, plus the content library and template collectors. | [Collectors](collectors.md) |
| `metrics/` | The metric and KPI calculations, including Business Application performance. | [Metrics Code](metrics-code.md) |
| `properties/` | The properties published on each object. | [Properties](properties.md) |
| `utils/`, `constants/`, `events/` | Reading from VCF Operations and vCenter, TLS, guest operations, collection health, shared names, and Windows event logs. | [Supporting Code](supporting-code.md) |

## Entry points

VCF Operations runs the adapter as a new Python process for each call. [`commands.cfg`](../../Management%20Pack/commands.cfg) maps each call to `python app/adapter.py <method>`:

| Method | When VCF Operations calls it | What it does |
| :--- | :--- | :--- |
| `adapter_definition` | When the pack is installed | Returns the object types, metrics, properties and settings that the pack declares. |
| `test` | When you click **Validate Connection** on an Adapter Instance | Connects to vCenter and reads its product name and version. |
| `collect` | Every collection cycle, every 5 minutes | Reads from vCenter and VCF Operations, and publishes the objects. |
| `endpoint_urls` | When VCF Operations asks which URLs the adapter uses | Returns an empty list. The pack declares no endpoints. |

Each call reads its input, such as the Adapter Instance and its credentials, from a file that VCF Operations writes, with the SDK's `AdapterInstance.from_input()`. It writes its result back with `send_results()`. See [The SDK](sdk.md).

## One collection cycle

`collect()` in `adapter.py` sets up the cycle, `_collect_cycle()` reads the settings and the shared inputs, and `_run_object_jobs()` runs the collectors:

1. Set the relationship mode of the result to `PER_OBJECT`, and start counting the warnings of the cycle (`utils/collection_health.py`).
2. Connect to vCenter with pyVmomi (`SmartConnect`), with the TLS arguments of the Adapter Instance.
3. Read the certificate that vCenter presents, in a separate TLS handshake (`tls.presented_thumbprint()`), for the Trust on First Use check.
4. Set the guest file transfer TLS mode for this cycle (`guest_http.configure()`).
5. Read the configuration files of the Adapter Instance from VCF Operations, under `SolutionConfig/`. A file that is missing or invalid gives an empty list and adds a problem, which is published later as an event on the vCenter object. See [Content Folder](content-folder.md).
6. Find the VCF Operations id of this vCenter's Adapter Instance in the vCenter adapter, by matching its `VCURL` identifier with the vCenter address. If none matches, the cycle ends with the error `No vCenter Adapter Instance found matching vCenter Server`.
7. Read the Operational Availability and the network speeds of this vCenter's hosts and clusters, once. The host, cluster, vCenter and Datacenter collectors share them.
8. Run nine jobs in a thread pool with five workers: cluster, host, VM, datastore, vCenter, vSphere World, Datacenter, content libraries, and Business Applications.
9. Publish the warning count and the first warning of the cycle on the vCenter object.
10. Stop counting, and write the timing of each job to the adapter log (`Collection Timing Summary`).

All jobs add their objects to one shared `CollectResult`, which is sent once at the end of the cycle. The log goes to `adapter.log` in the container, rotated at each run.

### Connections in one cycle

| Connection | Opened by | Purpose |
| :--- | :--- | :--- |
| pyVmomi session to vCenter | `_get_service_instance()`, once per cycle. Closed by an `atexit` handler. | All vSphere API reads. The five threads share its `ServiceInstance` content. |
| TLS handshake to vCenter | `tls.presented_thumbprint()`, once per cycle | Reads the certificate for the Trust on First Use check. Sends no credentials. |
| vSphere Automation REST session | `LibraryReader` in `collectLibraryData.py`, once per cycle, with a login and a logout | Content libraries and their items. |
| Suite API sessions to VCF Operations | `adapter_instance.suite_api_client`: one per configuration file read, and one for the rest of the cycle | Configuration files, stats, properties, resources and relationships. |

### Shared state

The jobs run on five threads in one process, and share these objects:

- The pyVmomi `ServiceInstance` and its `content`. Each read creates and releases its own container view, so threads do not share views. `tests/test_shared_connection.py` checks this with a fake.
- The `CollectResult`. Jobs add different objects to it.
- `TIMINGS` in `adapter.py`, the job timings for the summary.
- The module state of `utils/guest_http.py`: the guest TLS mode, the host thumbprints read from vCenter, and the hosts already logged as unchecked. A lock guards them, and `configure()` clears them at the start of each cycle.
- The collection health counter, a logging handler on the root logger for the length of the cycle.

None of this outlives the process, so nothing is carried from one cycle to the next.

## Design choices

- **One process per call.** This is how the SDK runs an adapter. A call keeps no state between cycles, so a restart loses nothing. Where history is needed, the pack reads it back from VCF Operations: the Periodic Cluster Check reads the timestamps of its own metrics (see [its page](../reference/metrics/periodic-cluster-check.md)), and the Trust on First Use check reads the thumbprint it recorded on the vCenter object.
- **One result per cycle.** All objects of a cycle are sent together, so VCF Operations gets one consistent set of values.
- **One collector per object type.** To find what a host gets, look in one file.
- **Shared inputs are read once.** Availability and network speed are read once per vCenter, not once per collector. Stats are read in batches of many objects. See [Supporting Code](supporting-code.md).
- **Failures stay local.** Each object catches its own errors and logs a warning. A job that fails is logged as an error by `_run_object_jobs()`, and the other jobs still run and publish. A value that could not be read is not published, so a chart shows a gap rather than a false 0.
- **`PER_OBJECT` relationships.** With the SDK's default mode, any relationship in the result makes VCF Operations remove every relationship that is not in it, including the manual members of Business Applications. `PER_OBJECT` replaces only the child lists of the objects in the result. See [Template and Content Library Design](template-and-library-design.md#parent-and-child-relationships).
- **Warnings are counted.** A warning only reaches the log, and the rest of the cycle is published, so a missing value would otherwise go unnoticed. The count and the first warning are published on the vCenter object and drive the **vCommunity Collection Warnings** alert. See [Supporting Code](supporting-code.md#utilscollection_healthpy).

## Conventions

- **Errors.** Raise when the code or a setting is wrong. Return a fallback only where the caller expects one, such as `None` for a file that could not be read. A read that a caller must not treat as complete raises instead of returning an empty list, for example `read_related()` in `utils/ops_stats.py`. Not every read follows this rule yet: see the limitations below.
- **Names.** New files use `snake_case.py`. Older `camelCase` files keep their names, so the history stays readable.
- **Failure isolation.** A failed step is logged as a warning or an error, and counted in the collection health of the cycle. It never stops another object.

## Limitations

- **Every value is up to one cycle old** (5 minutes), and a KPI is one cycle behind the stats it is built from.
- **Every Adapter Instance collects its whole vCenter.** Use one Adapter Instance per vCenter. The vSphere World object and the Business Application objects are published by every Adapter Instance, with the same values. See [vSphere World](../reference/metrics/vsphere-world-metrics.md).
- **Some reads publish from partial data.** When one batch of a stats or properties request fails, `read_latest_stats()` and `read_latest_properties()` log a warning and return the other batches. A caller that sums or averages the result can then publish a total built on part of the objects ([issue #60](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/60)). A few vCenter reads fall back to an empty list with a warning, such as the host licenses and the cluster list for Cluster Consumption.
- **Collection time grows with the inventory.** Large vCenters take longer per cycle. The Periodic Cluster Check handles a limited number of clusters per cycle, so a backlog is spread over several cycles. Guest work is limited to 30 minutes per cycle.
- **Windows guests need credentials.** The Windows properties and event logs run a PowerShell script in the guest through the vSphere Guest API. This needs VMware Tools and a Windows credential. See [TLS and Security Settings](../configuration-guide/tls-and-security.md).
- **The code runs in a Linux container.** The Python libraries are pinned in `adapter_requirements.txt`. See [Repository Layout](repository-layout.md).
