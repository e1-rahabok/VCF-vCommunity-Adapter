# Repository Layout

This page maps the repository: what each folder and file is, why it is there, and what it does. The pack itself is in `Management Pack/`. Everything else supports building, testing and documenting it.

## The top level

| Path | What it is | Why it is there |
| :--- | :--- | :--- |
| `Management Pack/` | The management pack. Everything in it goes into the `.pak` file, except the tests and local files. | The unit of packaging. The SDK builds the pak from this folder. |
| `docs/` | The documentation. [Documentation index](../README.md). | Users and contributors read it. It is not packed. |
| `tools/` | Scripts for contributors and administrators. Not packed, and not run in VCF Operations. See [Tools](../../tools/README.md). | Build, install, check and import, on a developer's machine. |
| `README.md` | The front page of the repository. | First thing a visitor reads. |
| `CONTRIBUTING.md` | How to contribute, and the rules for the documentation. | Keeps the docs in one structure. |
| `CLAUDE.md` | The instructions of the AI coding assistant used on this repository: build, install and test steps. | Keeps the assistant to the same steps as a contributor. |
| `.github/` | Issue and pull request templates, the CI workflow (`workflows/ci.yml`: the unit tests, the lint and the security checks on every pull request), Dependabot, and CODEOWNERS. | GitHub runs and uses them. |
| `ruff.toml` | The lint rules the CI workflow applies to `app` and `tests`. Kept outside the pack folder, so it is not packed. | Keeps the code to the same rules everywhere. |
| `.claude/` | Settings of the AI coding assistant. | Not used by the pack. |
| `LICENSE` | The license of the repository: the terms on which the code can be used. | Says how others may use and change the code. |
| `.gitignore` (root) | Files that are not committed. | Keeps local and generated files out of the repository. |

## Inside Management Pack/

| Path | What it is | Why it is there | Page |
| :--- | :--- | :--- | :--- |
| `app/` | The Python code the adapter runs. | The only code that runs in VCF Operations. | [App Folder](app-folder.md) |
| `content/` | The dashboards, reports, super metrics, alert definitions and configuration files. | Imported by VCF Operations, or read at runtime. | [Content Folder](content-folder.md) |
| `conf/` | The adapter kind icon, and a copy of the SDK's schema for the adapter description. | The SDK expects them in the pak. The schema is not used by the code. | [SDK](sdk.md) |
| `resources/` | `resources.properties`, the display name of the pack. | Shown in the VCF Operations UI. | [SDK](sdk.md) |
| `tests/` | The unit tests. | Checks the code without a live system. | [Tests](tests.md) |
| `manifest.txt` | The name, version, minimum VCF Operations version and platforms of the pack. | Read by the builder, and by the install script for the version. | [SDK](sdk.md#what-is-packaged) |
| `commands.cfg` | The four methods that VCF Operations can call, mapped to `app/adapter.py`. | How VCF Operations starts the adapter. | [App Folder](app-folder.md#entry-points) |
| `Dockerfile` | The container image of the adapter. It starts from a base image, installs the Python libraries, and copies `app/`. | The Cloud Proxy runs the adapter in this image. | [How It Works](../installation-guide/how-it-works.md) |
| `adapter_requirements.txt` | The Python libraries the adapter runs with, including the SDK runtime library. | Installed into the container image. | [SDK](sdk.md#versions) |
| `requirements.txt` | The SDK version, the same libraries, and the test library. This is the one place that names the SDK. | Installed with `pip` on a developer's machine. | [SDK](sdk.md#versions) |
| `eula.txt` | The license shown when the pack is installed. | Required by the pak. | [Installation](../installation-guide/installation.md) |
| `VCF-Operations-vCommunity.png` | The icon of the pack, shown in the UI. | Required by the pak. | [SDK](sdk.md#what-is-packaged) |
| `.gitignore` | Files that are not committed, such as `__pycache__`, logs, and the local test environment. | Keeps local files out of the repository. | |

## Files that are not used

- **`conf/describeSchema.xsd`** is not referenced anywhere in the repository. See [SDK](sdk.md).
- **`.DS_Store`** files, from macOS, are ignored by Git. They are not committed.
- **Placeholder folders** hold only a `.gitkeep` file, which keeps an empty folder in Git. They have no content yet, and no code reads them. `content/customgroups/`, `content/policies/` and `content/recommendations/` are for content that is not written yet. `content/files/reskndmetric/`, `content/files/topowidget/` and `content/files/txtwidget/` are kept for the content types their names give. Every other `.gitkeep` sits in a folder that also holds content, so it has no effect on the pak.

## Limitations

- **The pack's version is set in `manifest.txt` only.** The build, the install and the live validation all read it from there.
- **Generated files are in the working folder.** `__pycache__` and the test environment are created in the repository folder. They are ignored by Git, so they do not get committed, but they take space.
