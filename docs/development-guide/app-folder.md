# The App Folder

`Management Pack/app/` is the Python code of the adapter. It is the only folder that runs in VCF Operations. The Dockerfile copies it into the container that the Cloud Proxy runs, together with `commands.cfg` and `adapter_requirements.txt`. The rest of the repository does not reach the container.

Code: [`Management Pack/app/`](../../Management%20Pack/app/)

## What it does

The adapter reads the ESXi and VM data that the vCenter adapter of VCF Operations does not collect, and publishes it onto the existing vCenter objects in VCF Operations, under the `vCommunity|` key prefix. It does this in three ways:

- **Properties**: text and number settings, such as an advanced setting or a license expiry date.
- **Metrics**: numbers over time, such as the Operational Availability of a cluster.
- **KPIs**: a score from 0 to 100 built from many sub-metrics. See [Metrics Code](metrics-code.md).

## What is in it

| Path | What it is | Page |
| :--- | :--- | :--- |
| `adapter.py` | The entry point. Runs the test, collect and endpoint methods. | This page |
| `definition.py` | The adapter definition: the object types, groups, metrics, properties and parameters that VCF Operations shows. Also the KPI table helpers and `KPI_UNITS`. | [Metrics Code](metrics-code.md) |
| `collectors/` | One collector per VCF Operations object type. Each one calls the modules for its objects. | [Collectors](collectors.md) |
| `metrics/` | The calculation of metrics and KPIs. | [Metrics Code](metrics-code.md) |
| `properties/` | The properties published on each object. | [Properties](properties.md) |
| `utils/`, `constants/`, `events/` | Shared reading of VCF Operations, TLS and guest handling, names, and Windows event logs. | [Supporting Code](supporting-code.md) |

## Entry points

VCF Operations runs the adapter as a separate Python process for each call. The commands are in [`commands.cfg`](../../Management%20Pack/commands.cfg), which maps each call to `python app/adapter.py <method>`:

| Method | When VCF Operations calls it | What it does |
| :--- | :--- | :--- |
| `adapter_definition` | When the pack is installed | Returns the object types, metrics and properties the pack declares. |
| `test` | When you test an Adapter Instance | Connects to the vCenter and reads its content. Nothing else. |
| `collect` | Every collection cycle, every 5 minutes | Reads from vCenter and VCF Operations, and publishes the objects. |
| `endpoint_urls` | When VCF Operations asks which URLs the adapter uses | Returns none. The pack declares no endpoints. |

The input of each call, such as the Adapter Instance and its credentials, is read from a file that VCF Operations writes, with the SDK's `AdapterInstance.from_input()`. The result is written back with `send_results()`. See [SDK](sdk.md).

## One collection cycle

The `collect` method, in `adapter.py`, runs these steps. Steps 1 to 4 are in `_collect_cycle`, and step 5 is in `_run_object_jobs`:

1. Read the Adapter Instance settings, and the configuration files that choose what is collected. These are read from VCF Operations, under `SolutionConfig`. See [Content Folder](content-folder.md).
2. Connect to the vCenter, once.
3. Find the VCF Operations id of this vCenter's adapter instance, by matching its URL.
4. Read the Operational Availability and the Network Speed of the vCenter's hosts and clusters, once. Several collectors use them.
5. Run the seven collectors in parallel, in five threads: cluster, host, VM, datastore, vCenter, vSphere World and Datacenter.
6. Each collector adds its objects to one result. The result is sent once, at the end.
7. The timing of each step is written to the adapter log.

Logs go to `adapter.log` in the container, rotated at each run.

## Why it is built this way

- **One process per call.** This is how the SDK runs an adapter. A call holds no state between cycles, so a restart of the pack loses nothing. Where state is needed, the Periodic Cluster Check reads the timestamps of its own published metrics, see [its page](../reference/metrics/periodic-cluster-check.md).
- **One result per cycle.** All objects of a cycle are sent together, so VCF Operations sees one consistent set of values.
- **Collectors per object type.** Each VCF Operations object type has one file. A reader looking for "what does a Host get" finds one place.
- **Shared inputs read once.** Availability and network speed are read once per vCenter, not once per collector. Stats are read in batches of many objects, not one request per object. See [Supporting Code](supporting-code.md).
- **Failures stay local.** Each object catches its own errors and writes a warning. A failing collector is logged as an error by `collect`, and the others still run and publish. One failing cluster, host or collector does not stop the others. The result of a failed part is missing, not a wrong number.
- **Missing is not zero.** A value that could not be read is not published, so a chart shows a gap rather than a false 0.

## Conventions

- **Errors.** Raise when the code is wrong, or a setting is wrong. Return a value only where the caller expects a fallback, such as `None` for a file that could not be read. A failed read of vCenter or VCF Operations is never returned as an empty list: it raises, so the caller cannot publish "no objects" for a read that did not happen.
- **Names.** New files are `snake_case.py`. Existing `camelCase` files keep their names, so the history stays readable.
- **Failure isolation.** A failed step is logged as a warning or an error, and counted in the Collection Warnings of the cycle. It never stops another object.

## Limitations

- **Every value is up to one cycle old**, 5 minutes, and a KPI is one cycle behind the stats it is built from.
- **Every account collects the whole vCenter.** One Adapter Instance per vCenter. The vSphere World object is published by every account, with the same values. See [vSphere World](../reference/metrics/vsphere-world-metrics.md).
- **Collection time grows with the inventory.** Large vCenters take longer per cycle. The Periodic Cluster Check is capped at a number of clusters per cycle, so a backlog is spread over several cycles.
- **Windows guests need credentials.** Some properties and the Windows event logs run a PowerShell script inside the guest, through the vSphere Guest API. That needs VMware Tools in the guest and a credential. See [TLS and Security Settings](../configuration-guide/tls-and-security.md).
- **The code runs in a Linux container.** The Python libraries are pinned in `adapter_requirements.txt`. See [Repository Layout](repository-layout.md).
- **There is no local state.** This is a benefit, but it also means that anything that needs history must read it back from VCF Operations.
