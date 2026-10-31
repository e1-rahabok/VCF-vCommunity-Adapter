# Dashboards Show Default Sections or Empty Widgets After an Install

After you install the pack, or import one of its dashboards, the dashboard can look wrong: section headings say `Section`, or widgets are empty. This page explains why it happens, how to tell it is still loading and not broken, and what to do.

## What you see

- Section headings read `Section` instead of their names, such as `KEY METRICS`.
- Widgets show no data, or the layout is the default one.
- The dashboard loads, but it looks different from the file the pack ships.

## Why it happens

When a dashboard is imported, VCF Operations stores its widgets first and resolves their settings later, in the background. Until the settings are resolved, a widget shows its default title and no configuration.

The resolution can take a long time. On the test instance it took more than ten minutes, and the dashboard finished resolving only after it was opened in the browser. The delay is not corruption: the same file imported correctly on another VCF Operations instance.

A copy made before the settings are resolved keeps the unresolved state. This was observed for a clone of the dashboard, which was made before the original resolved and stayed as `Section`. A Summary tab copy made during an install probably works the same way, but that is not confirmed.

So a clone can stay as `Section` even after the original dashboard is correct.

## What to do

1. **Open the original dashboard in the browser** and wait. Refresh the page if the load takes more than a few minutes. Once it renders with its section names, the settings are resolved.
2. **Check the original, not a copy.** If the original looks right and a clone does not, the clone was made too early. Delete the clone and clone it again.
3. **Rebind the Summary tab** after the original has resolved, so the Summary copy is made from the resolved dashboard. The script in [`tools/summary_dashboard/`](../../tools/summary_dashboard/summary_dashboard.md) does this.
4. **Do not judge the state by a config field.** A widget can show its real title while its `config` field is still empty. Use the widget titles, as the [Summary Dashboard Script](../../tools/summary_dashboard/summary_dashboard.md) does.

## Check the state from the API

The dashboard's widgets are readable through the same request the page makes. This is a read-only check, from `tools/summary_dashboard/` with `VCFOpsUIClient`:

```python
cfg = ui.get_dashboard_config(tab_id)["dashboardConfig"]["tabConfigs"][0]
for w in cfg["widgets"]:
    if w.get("key") == "Section":
        print(w.get("title"))
```

If every title is `Section`, the settings are not resolved yet. If they show real names, they are.

## When it is not a delay

If a dashboard still shows `Section` after you have opened the original in the browser and waited several hours, the delay is not the cause. Then:

- Check that the dashboard JSON in the pack has the section names. The names are in `widgets[].title` for widgets of type `Section`.
- Check the VCF Operations version. This was tested on VCF Operations 9.1.1.
- Collect the appliance logs for the import. Look in `/storage/log/vcops/log/` for `DashboardImporter` lines in `vcops-bridge` and for audit entries `DASHBOARD.ADD_TAB` in `web.audit.log`.

## Related

- [Summary Dashboards](../configuration-guide/summary-dashboards.md): replacing the Summary tab of an object type.
- [Symptoms](symptoms.md): other things that can go wrong while the pack runs.
