# Binding Dashboards to Object Types from the Pak

What was tested about binding a pack dashboard to an object type's Summary tab at install time, and the packaging this needs. This page is for contributors who change the build. The steps for administrators are in [Summary Dashboards](../configuration-guide/summary-dashboards.md).

**Status:** binding at install works when the binding file is added to the pak after `mp-build` runs. That step has been tested but is **not in the build script yet**, so the pak built from this repository does not bind anything. The six Summary dashboards in `content/dashboards/` are installed disabled and unbound. Administrators bind them with the [Summary Dashboard Script](../../tools/summary_dashboard/summary_dashboard.md).

## What mp-build does with content/dashboards/

When it assembles the pak, `mp-build` runs the SDK's `build_subdirectories` function (in `mp_build.py`) on `content/dashboards/`. It:

- moves each loose file into a subfolder of its own, named after the file in lower case, so `Overall Daily Check.json` becomes `overall daily check/Overall Daily Check.json`;
- stops the build with exit code 1 if a `.properties` file is loose in `content/dashboards/`.

Folders inside `dashboards/` are left alone, and a `.properties` file inside a dashboard's own folder is accepted.

## What was tested

| What was tried | Result |
| :--- | :--- |
| `dashboards.properties` loose in `content/dashboards/`, before `mp-build` | The build stops with exit code 1. |
| `dashboards.properties` in `content/dashboards/<folder>/resources/` | The build accepts it. The install imports the dashboard but does **not** bind it. |
| The same file added to the built `.pak` at `content/dashboards/dashboards.properties` | The install accepts the pak, and all six Summary tabs are bound to the pak's dashboards. |

The binding file has one line per dashboard folder, in the form `<folder>=<AdapterKind>:<ResourceKind>`. The key is the folder name and is case-sensitive. For example:

```
VMFolder=VMWARE:VMFolder
```

## Why the file is added after the build

`mp-build` refuses a loose `.properties` file in `content/dashboards/`, but the installer reads the binding from exactly that place. The management pack factory's own builder writes the file directly and doesn't use `mp-build`. So the file has to be added to the built pak, at the place the installer reads.

The built pak has no file list, checksum or signature that the SDK checks: its outer manifest has no file-list key, the SDK source has no hashing code, and an unsigned pak installs with signature checks skipped. An install of the modified pak succeeded, which confirms this.

## Caveats

- Binding copies the dashboard into a Summary template. A copy made before the dashboard's settings are resolved keeps the unresolved state. See [Dashboards Show Default Sections or Empty Widgets After an Install](../troubleshooting-guide/dashboards-after-install.md).
- Binding again creates a new copy. The factory's binding notes say the earlier copy may be left behind. This was not checked here.
- The binding was tested only on VCF Operations 9.1.1.

## Uninstalling and reinstalling

Uninstalling the pak from the UI removed the pak's dashboards and their Summary templates (the audit log records `DASHBOARD.DELETE` and `DASHBOARD.DELETE_TEMPLATE`). It also removed the Adapter Instance, so a restart or validation afterwards has nothing to check until an Adapter Instance is created again. A clean reinstall imported all the dashboards again.

## Open items

- Add the post-build step to `tools/build/build.ps1`, and review it before it goes into the repository.
- Test whether a Summary copy made after its source has resolved keeps its settings.
- Check on another VCF Operations build whether binding at install works the same way.
