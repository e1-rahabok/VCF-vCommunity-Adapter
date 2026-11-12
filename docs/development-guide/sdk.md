# The VCF Operations Integration SDK

The pack is built with the VCF Operations Integration SDK, the framework that lets a program run as a VCF Operations adapter. The SDK defines how VCF Operations calls the program, how the program describes its objects, and how it returns values. This page covers the parts of the SDK this pack uses. For everything else, use the SDK documentation.

## SDK documentation

- **SDK documentation:** [github.com/vmware/vmware-vcf-operations-integration-sdk, docs folder](https://github.com/vmware/vmware-vcf-operations-integration-sdk/tree/main/docs). The reference for the SDK.
- **SDK repository:** [github.com/vmware/vmware-aria-operations-integration-sdk](https://github.com/vmware/vmware-aria-operations-integration-sdk), the repository the [README](../../README.md) links to.

The SDK documentation is written for any adapter. The sections below cover only what this pack needs, and say where each part is used.

## The parts this pack uses

| SDK part | What it does | Where the pack uses it |
| :--- | :--- | :--- |
| Command interface | VCF Operations runs the adapter with a method name: `adapter_definition`, `test`, `collect` or `endpoint_urls`. | [`commands.cfg`](../../Management%20Pack/commands.cfg), `main()` in `adapter.py` |
| `AdapterInstance` | Reads the input of a call: the Adapter Instance, its settings and its credentials. | `adapter.py`, for every call |
| `AdapterDefinition`, `define_object_type`, `Units` | Declares the object types, groups, metrics, properties, units and Adapter Instance settings. The pack declares its own object types (Content Library, Library Item, VM Template) here too. | `get_adapter_definition()` in `definition.py` |
| `Object`, `Key`, `Identifier`, `add_child` | An object in VCF Operations that the pack sets values on. `Key` and `Identifier` create the pack's own objects, and `add_child` links a Library Item to its Content Library. | Every collector, and every metric and property module |
| `CollectResult`, `RelationshipUpdateModes` | The result that holds all objects of a cycle. The pack sets `PER_OBJECT`, so only the objects in the result have their child lists replaced. | `collect()` in `adapter.py`, see [App Folder](app-folder.md#design-choices) |
| `with_event`, `Criticality` | An event on an object. The pack raises one warning event per configuration file problem on the vCenter object. | `collectors/vcenter/collectvCenterData.py` |
| `SuiteApiClient` | A client for the VCF Operations REST API (the Suite API), to read objects, stats, properties and relationships. | `utils/ops_stats.py`, `utils/ops_inventory.py`, `adapter.py`, the collectors, `business_app_performance.py`, `resource_pool_counts.py` and `properties/vcenter/certificate.py` |
| `TestResult`, `EndpointResult` | The results of the `test` and `endpoint_urls` calls. | `test()` and `get_endpoints()` in `adapter.py` |
| Logging and `Timer` | Writes to the adapter log, and times a step. | `adapter.py` and the modules |

The pack talks to VCF Operations only through the SDK's calls, results and Suite API client. It reads vCenter directly with pyVmomi and, for content libraries, with the vSphere Automation REST API. Neither is part of the SDK.

## How a call works

VCF Operations starts a new process for each call. The process reads its input from a file, runs one method, and writes its result to a file. Nothing stays in memory between two cycles, so a collection cycle is one run of the `collect` method, every 5 minutes. See [App Folder](app-folder.md).

## What is packaged

A pack is a `.pak` file. The Management Pack Builder (`mp-build`) builds it from the `Management Pack` folder:

| File or folder | What it is |
| :--- | :--- |
| `manifest.txt` | The name, version, minimum VCF Operations version (8.18.0), supported platforms (Linux) and adapter kind of the pack. The install script reads the version from it. |
| `commands.cfg` | The four methods that VCF Operations can call. |
| `Dockerfile`, `adapter_requirements.txt` | The container image that the Cloud Proxy runs: a base image, the Python libraries, and the `app` folder. |
| `app/` | The Python code. See [App Folder](app-folder.md). |
| `content/` | The dashboards, reports, super metrics, alerts and configuration files. See [Content Folder](content-folder.md). |
| `conf/` | The adapter kind icon, and a copy of the SDK's schema for the adapter description. The code does not read the schema. |
| `resources/resources.properties` | The display name and description of the pack, shown in the VCF Operations UI. |
| `eula.txt` | The license shown when the pack is installed. |

[Repository Layout](repository-layout.md) lists every file.

## Versions

The SDK build tool version is set in one place, `Management Pack/requirements.txt`: currently **1.3.1**. Developer machines, the tests and the build tools all install it from there.

- **The container** runs the SDK's runtime library, `vmware-aria-operations-integration-sdk-lib`, which provides the `aria` package the adapter imports. The base image doesn't contain it, so its version is pinned in `adapter_requirements.txt`. The base image tag (`python-1.2.0`) is the image's own version, not the SDK's.
- **The build** ([Build Script](../../tools/build/build.md)) needs SDK 1.3 or later.
- **Python:** SDK 1.3.1 requires Python 3.9 to 3.12. On Python 3.13, `pip` installs a much older SDK version instead. Use 3.12, as CI does.

To change the SDK, change the line in `requirements.txt`, then build and validate the pack. A new base image is a change to the `Dockerfile` and needs the same checks.

## Limitations

- **The SDK documentation is general.** This page covers only what the pack uses.
- **Each call starts a process,** so the start-up cost is paid at every call. For a collection every 5 minutes this is small compared to the work of the cycle.
- **Two SDK packages are involved.** The build tool (in `requirements.txt`) and the runtime library (in `adapter_requirements.txt`) are separate packages. Keep them compatible when either changes.
