# Repository Layout

What each folder and file in the repository is, and why it is there. The pack itself is in `Management Pack/`. Everything else supports building, testing and documenting it.

## Top level

| Path | What it is | Why it is there |
| :--- | :--- | :--- |
| `Management Pack/` | The management pack: code, content, tests and packaging files. | `mp-build` builds the `.pak` file from this folder. |
| `docs/` | The documentation. See the [documentation index](../README.md). | For users and contributors. Not packed. |
| `tools/` | Scripts that run on a workstation: build, install, restart, validate, screenshots, Summary dashboard binding, the bulk importer, the KPI equivalence test and the docs link check. See [Tools](../../tools/README.md). | Not packed, and never run in VCF Operations. |
| `README.md` | The front page of the repository. | The first page a visitor reads. |
| `CONTRIBUTING.md` | How to contribute, and the documentation rules. | Keeps contributions and docs consistent. |
| `SECURITY.md` | How to report a vulnerability. | GitHub links to it from the Security tab. |
| `SUPPORT.md` | What support the project offers. | GitHub links to it when someone opens an issue. |
| `CLAUDE.md` | Instructions for the AI coding assistant used on this repository: build, install and test steps. | Keeps the assistant to the same steps as a human contributor. |
| `.claude/` | Settings of the AI coding assistant. | Not used by the pack. |
| `.github/` | Issue and pull request templates, CODEOWNERS, Dependabot, and two workflows. `workflows/ci.yml` runs the unit tests, lint, security scan and dependency audit on every pull request and every push to `main`. `workflows/badges.yml` counts the files and lines on `main` for the README badges. | Used by GitHub. |
| `ruff.toml` | The lint rules that CI applies to `app` and `tests`. Kept outside the pack folder so it is not packed. | The same rules everywhere. |
| `.gitignore` | Files that are not committed, such as `.DS_Store`, local Python environments and `.secrets/`. | Keeps local and generated files out of the repository. |

## Inside Management Pack/

| Path | What it is | Why it is there | Page |
| :--- | :--- | :--- | :--- |
| `app/` | The Python code of the adapter. | The only code that runs in VCF Operations. | [App Folder](app-folder.md) |
| `content/` | Dashboards, reports, views, super metrics, alert and symptom definitions, and configuration files. | Imported by VCF Operations at install, or read at runtime. | [Content Folder](content-folder.md) |
| `conf/` | The adapter kind icon, and a copy of the SDK's schema for the adapter description. | The SDK expects them in the pak. The code doesn't read the schema. | [The SDK](sdk.md) |
| `resources/` | `resources.properties`: the display name, description and vendor of the pack. | Shown in the VCF Operations UI. | [The SDK](sdk.md) |
| `tests/` | The unit tests. | Check the code without a live system. Not copied into the container image. | [Tests](tests.md) |
| `manifest.txt` | The name, version, minimum VCF Operations version and platforms of the pack. | Read by `mp-build`, and by the install and validation scripts for the version. | [The SDK](sdk.md#what-is-packaged) |
| `commands.cfg` | The four methods VCF Operations can call, mapped to `app/adapter.py`. | How VCF Operations starts the adapter. | [App Folder](app-folder.md#entry-points) |
| `Dockerfile` | The adapter's container image. It starts from the SDK's base image, installs the Python libraries and copies `commands.cfg` and `app/`. | The Cloud Proxy runs the adapter in this image. | [How It Works](../installation-guide/how-it-works.md) |
| `adapter_requirements.txt` | The Python libraries the adapter runs with, including the SDK runtime library. | Installed into the container image. | [The SDK](sdk.md#versions) |
| `requirements.txt` | The SDK build tool, the runtime libraries (by including `adapter_requirements.txt`), and `cryptography` for the TLS tests. The only place that names the SDK build tool. pytest is installed separately. | Installed with `pip` on a developer's machine and in CI. | [The SDK](sdk.md#versions) |
| `eula.txt` | The license shown when the pack is installed. | Required in the pak. | [Installation](../installation-guide/installation.md) |
| `VCF-Operations-vCommunity.png` | The icon of the pack in the UI. | Required in the pak. | [The SDK](sdk.md#what-is-packaged) |
| `.gitignore` | Local files of the pack folder that are not committed, such as `build/`, `logs`, `config.json`, `__pycache__` and the local test environment. | Keeps build output and local settings out of the repository. | |

## Files that are not used

- **`conf/describeSchema.xsd`** is not referenced anywhere in the repository. See [The SDK](sdk.md).
- **Placeholder folders** hold only a `.gitkeep` file, which keeps an empty folder in Git. No code reads them. `content/customgroups/`, `content/policies/` and `content/recommendations/` are for content not written yet. `content/files/reskndmetric/`, `content/files/topowidget/` and `content/files/txtwidget/` are kept for the content types their names give. Every other `.gitkeep` is in a folder that also holds content, and has no effect on the pak.

## Limitations

- **The pack's version is set only in `manifest.txt`.** The build, install and live validation all read it from there.
- **Generated files are created in the working folder.** `__pycache__`, the `mp-build` output and the test environment are created inside the repository folder. Git ignores them, but they take disk space.
