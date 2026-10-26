# The VCF Operations Integration SDK

The pack is built with the VCF Operations Integration SDK. The SDK is the framework that lets a program run as an adapter of VCF Operations: it defines how VCF Operations calls the program, how the program describes its objects, and how it returns the values. This page explains the parts this pack uses. It does not replace the SDK documentation.

## Where to read the SDK documentation

- **SDK documentation:** [github.com/vmware/vmware-vcf-operations-integration-sdk, docs folder](https://github.com/vmware/vmware-vcf-operations-integration-sdk/tree/main/docs). This is the reference for the SDK.
- **SDK repository:** [github.com/vmware/vmware-aria-operations-integration-sdk](https://github.com/vmware/vmware-aria-operations-integration-sdk), the repository the [README](../../README.md) links to.

The SDK documentation is written for any adapter. The sections below only cover what this pack needs, and they say where each part is used.

## The parts this pack uses

| SDK part | What it does | Where the pack uses it |
| :--- | :--- | :--- |
| Command interface | VCF Operations runs the adapter with a method name: `adapter_definition`, `test`, `collect`, `endpoint_urls`. | [`commands.cfg`](../../Management%20Pack/commands.cfg), `main()` in `adapter.py` |
| `AdapterInstance` | Reads the input of a call: the Adapter Instance, its settings and its credentials. | `adapter.py`, for every call |
| `AdapterDefinition` | Declares the object types, metrics, properties and units of the pack. The units are in `Units`. | `get_adapter_definition()` in `adapter.py` |
| `Object`, `CollectResult` | An object of VCF Operations that the pack sets metrics and properties on, and the result that holds all objects of a cycle. | Every collector, and every metric and property module |
| `SuiteApiClient` | Client for the VCF Operations REST API (the Suite API), to read objects, stats and properties. | `utils/ops_stats.py`, `utils/ops_inventory.py`, and `adapter.py` |
| `TestResult`, `EndpointResult` | The results of the `test` and `endpoint_urls` calls. | `test()` and `get_endpoints()` in `adapter.py` |
| Logging and `Timer` | Writes to the adapter log, and measures the time of a step. | `adapter.py` and the modules |

The pack talks to VCF Operations through the SDK's calls and results, and through its Suite API client. It reads vCenter directly with pyVmomi, which is not part of the SDK.

## How a call works

VCF Operations starts a new process for each call. The process reads its input from a file, runs one method, and writes the result to a file. Nothing stays in memory between two cycles. A collection cycle is therefore one run of the `collect` method, every 5 minutes. See [App Folder](app-folder.md).

## What is packaged

A pack is a `.pak` file. The Management Pack Builder (`mp-build`) builds it from the repository:

| File or folder | What it is |
| :--- | :--- |
| `manifest.txt` | The name, version, minimum VCF Operations version (8.18.0), supported platforms (Linux) and adapter kind of the pack. The install script uses its version. |
| `commands.cfg` | The four methods that VCF Operations can call. |
| `Dockerfile`, `adapter_requirements.txt` | The container image the Cloud Proxy runs: a base image, the Python libraries, and the `app` folder. |
| `app/` | The Python code. See [App Folder](app-folder.md). |
| `content/` | The dashboards, reports, super metrics and configuration files. See [Content Folder](content-folder.md). |
| `conf/` | The adapter kind icon, and a copy of the SDK's schema for the adapter description. The code does not read the schema. |
| `resources/resources.properties` | The display name of the pack, shown in the VCF Operations UI. |
| `eula.txt` | The license shown when the pack is installed. |

See [Repository Layout](repository-layout.md) for every file.

## Versions

The SDK version is set in one place: `Management Pack/requirements.txt`, currently **1.3.1**, the latest release. The developer's machine, the tests and the build tools use it from there.

- **The container** gets the SDK from its base image, named in the `Dockerfile`. The base image's tag (`python-1.2.0`) is the image's own version, not the SDK's. The base image is built with the SDK 1.3 or later, as the `Dockerfile` comment says. The container no longer pins the SDK's runtime library separately, so it is the base image that decides it.
- **The build** ([Build Script](../../tools/build/build.md)) needs the SDK 1.3 or later.
- **Python:** the SDK 1.3.1 package requires Python 3.9 to 3.12. Use one of those on the developer's machine.

To change the SDK, change the one line in `requirements.txt`, then build and validate the pack. A new base image is a change to the `Dockerfile` and needs the same check.

## Limitations

- **The SDK documentation is general.** This page covers the parts the pack uses. For anything else, use the links above.
- **Each call starts a process.** The start-up cost is paid at each call. For a collection every 5 minutes, this is small against the work of the cycle.
- **The container's SDK version is not set in this repository.** It is whatever the base image bundles. Check it with each build, see [Versions](#versions).
