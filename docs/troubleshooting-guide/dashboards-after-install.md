# Dashboards Show Default Sections or Empty Widgets After an Install

After you install the pack, or import one of its dashboards, a dashboard can look wrong for a while: section headings read `Section`, or widgets are empty. This page explains why, how to tell a dashboard that is still loading from a broken one, and what to do.

## What you see

- Section headings read `Section` instead of their names, such as `KEY METRICS`.
- Widgets show no data, or the default layout.
- The dashboard loads, but looks different from the file the pack ships.

## Why it happens

When VCF Operations imports a dashboard, it stores the widgets first and resolves their settings later, in the background. Until then, each widget shows its default title and no configuration.

This can take more than ten minutes, and a dashboard may only finish resolving after someone opens it in the browser. The file itself is not damaged: the same file imports correctly on other instances.

A copy made before the settings are resolved keeps the unresolved state. A clone made too early stays as `Section`, even after the original is correct. A Summary tab binding also makes a copy of the dashboard, so bind only after the original has resolved.

## What to do

1. **Open the original dashboard in the browser** and wait. Refresh the page if it takes more than a few minutes. When the section names show, the settings are resolved.
2. **Check the original, not a copy.** If the original looks right and a clone does not, the clone was made too early. Delete it and clone again.
3. **Bind Summary tabs after the original has resolved**, so that the Summary copy is made from the resolved dashboard. The [Summary Dashboard Script](../../tools/summary_dashboard/summary_dashboard.md) binds or rebinds one.
4. **Judge by the widget titles, not by the `config` field.** A widget can show its real title while its `config` field is still empty.

## Check the state from the API

The dashboard's widgets can be read with the same request the page makes. This read-only check runs from `tools/summary_dashboard/`, with `VCFOpsUIClient`:

```python
cfg = ui.get_dashboard_config(tab_id)["dashboardConfig"]["tabConfigs"][0]
for w in cfg["widgets"]:
    if w.get("key") == "Section":
        print(w.get("title"))
```

If every title is `Section`, the settings are not resolved yet. If the real names show, they are.

## When it is not a delay

If a dashboard still shows `Section` several hours after you opened the original in the browser, something else is wrong. Then:

- Check that the dashboard JSON in the pack has the section names, in `widgets[].title` of the widgets of type `Section`.
- Check the VCF Operations version. The dashboards were tested on VCF Operations 9.1.1.
- Collect the appliance logs for the import. In `/storage/log/vcops/log/`, look for `DashboardImporter` lines in the `vcops-bridge` log and for `DASHBOARD.ADD_TAB` entries in `web.audit.log`.

## Related

- [Summary Dashboards](../configuration-guide/summary-dashboards.md): replacing the Summary tab of an object type.
- [Symptoms](symptoms.md): other problems while the pack runs.
