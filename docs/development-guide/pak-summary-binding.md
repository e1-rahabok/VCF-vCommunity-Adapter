# Binding Dashboards to Object Types from the Pak

This page records what was tested about binding a pack dashboard to an object type's Summary tab at install time, and about the packaging that binding needs. It is for contributors who change the build. The steps for an administrator are in [Summary Dashboards](../configuration-guide/summary-dashboards.md).

**Status:** the binding works when the binding file is added to the pak after `mp-build` runs. That step is tested but **not yet in the build script**, so it is not in the repo's pak.

## What `mp-build` does with `content/dashboards/`

The SDK's `build_subdirectories` function in `mp_build.py` runs on `content/dashboards/` when the pak is assembled. It:

- moves each loose file in the folder into its own subfolder, named after the file in lowercase, so `Overall Daily Check.json` becomes `overall daily check/Overall Daily Check.json`;
- stops the build with exit code 1 if a `.properties` file is loose in `content/dashboards/`.

A folder inside `dashboards/` is left alone. A `.properties` file inside a dashboard's own folder is accepted.

## What was tested

| What was tried | Result |
| :--- | :--- |
| `dashboards.properties` loose in `content/dashboards/`, before `mp-build` | Build stops with exit code 1 |
| `dashboards.properties` in `content/dashboards/<folder>/resources/` | Build accepts it. The install imports the dashboard but does **not** bind it. |
| The same file appended to the built `.pak` at `content/dashboards/dashboards.properties` | Install accepts the pak. All six Summary tabs are bound to their pak dashboards. |

The binding file has one line per dashboard folder, in the form `<folder>=<AdapterKind>:<ResourceKind>`. The key is the folder name, and it is case-sensitive. For example:

```
VMFolder=VMWARE:VMFolder
```

## Why the file is added after the build

`mp-build` refuses a loose `.properties` file in `content/dashboards/`, but the installer reads the binding from that exact place. The factory's own builder writes the file directly and does not use `mp-build`. So the file has to be added after the build, to the same place the installer reads.

The built pak has no file list, checksum or signature that the SDK checks: its outer manifest has no file-list key, the SDK source has no hashing code, and the unsigned pak installs with signature checks skipped. The appended file installed without an error, so this was confirmed by an install, not only by reading the code.

## Caveats

- A binding copies the dashboard into a Summary template. A copy made before the dashboard's settings are resolved keeps the unresolved state. See [Dashboards Show Default Sections or Empty Widgets After an Install](../troubleshooting-guide/dashboards-after-install.md).
- Binding again creates a new copy. The earlier copy may be left behind. This was noted in the factory's pak binding notes, and it was not checked here.
- The binding was tested on VCF Operations 9.1.1 only.

## Uninstalling and reinstalling

Uninstalling the pak from the UI removed the pak's dashboards and their Summary templates (the audit log records `DASHBOARD.DELETE` and `DASHBOARD.DELETE_TEMPLATE`). It also removed the adapter instance, so a later restart or validation has nothing to check until an adapter instance is created again. A clean reinstall re-imported all the dashboards.

## Open items

- Add the post-build step to `tools/build/build.ps1`, and review it before it goes into the repo.
- Test whether a Summary copy made after its source has resolved keeps the config.
- Confirm on another VCF Operations build whether the install-time binding works the same way.
