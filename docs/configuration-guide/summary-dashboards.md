# Summary Dashboards

Each object in VCF Operations has a **Summary** tab. By default it shows the built-in summary page for that object type. You can replace it with one of your own dashboards, for example a dashboard that shows the settings this pack collects. This page explains how, for every object type, and what to watch for.

Use the built-in UI for one object type. Use the script in this page for several. It does the same thing as **Manage Summary Dashboards** in the UI, so the result is the same.

## Before you start

- You need a dashboard. It can be new: create it in the UI, or import a JSON file under the **...** menu on **Dashboards**. The script does not create or import dashboards. It binds an existing one, by name and UUID, so note its UUID once it exists. To list the UUIDs on the instance, run this from `tools/summary_dashboard`:

  ```python
  from ui_client import VCFOpsUIClient
  with VCFOpsUIClient(host, user, password, verify_ssl=False) as ui:
      for d in ui.list_dashboards():
          print(d["id"], "|", d["name"])
  ```
- You need Python 3 with the `requests` library, and an account that can manage dashboards. The local `admin` account works.
- The script is in [`tools/summary_dashboard/`](../../tools/summary_dashboard/). Its full reference is [Summary Dashboard Script](../../tools/summary_dashboard/summary_dashboard.md).

## Step 1: find the object type

The object type is the one you see on the object's Summary panel, under **Object Type**. Use that name, not the name of a parent object.

Most object types map to one resource kind. Folders are the exception, and the next section covers them.

To list the resource kinds of an adapter, with their current Summary assignments, run this from `tools/summary_dashboard`:

```python
from ui_client import VCFOpsUIClient
with VCFOpsUIClient(host, user, password, verify_ssl=False) as ui:
    for e in ui.get_resource_kind_list("VMWARE")["resourceKindList"]:
        print(e["resourceKind"], "|", e["name"], "|", e["resourceKindId"], "|", e["resourceKindTemplate"])
```

`name` is the object type as the UI shows it. `resourceKind` is the key the script takes. `resourceKindTemplate` is what the Summary tab shows now: `Summary Detail` means the built-in page.

## Folders are five object types

The VMware adapter has five folder kinds, and each one has its own Summary tab. Binding one does not change the others.

| Object type in the UI | Resource kind key |
| :--- | :--- |
| Virtual Machine Folder | `VMFolder` |
| Host Folder | `HostFolder` |
| Datastore Folder | `DatastoreFolder` |
| Network Folder | `NetworkFolder` |
| Folder | `Folder` |

The plain `Folder` is not the Virtual Machine Folder. Check the object type on the Summary panel before you choose the key. If you bind the wrong kind, the object you looked at does not change, and you can undo it with `--restore`.

## Step 2: bind the dashboard

From `tools/summary_dashboard`, set the connection in the environment and run the script. Use the dashboard's name exactly, and its UUID:

```powershell
$env:VCFOPS_HOST = 'vcfops.example.com'
$env:VCFOPS_USER = 'admin'
$env:VCFOPS_PW   = '...'
python set_summary_dashboard.py VMWARE VMFolder "My Summary Dashboard" 00000000-0000-0000-0000-000000000000
```

The script prints the Summary tab as the instance reports it afterwards:

```
VMWARE:VMFolder summary tab now: {'tabId': '...', 'isDashboard': True}
```

`isDashboard: True` means the object type now shows your dashboard.

Do not put the password in a file you keep, or in your shell history. Set it for the session, or prompt for it.

## Step 3: check the result

Open an object of that type and open its **Summary** tab. It should show your dashboard, not **Recommended Actions** and the built-in charts.

To check the template itself, read it back with the script's functions, as the [Summary Dashboard Script](../../tools/summary_dashboard/summary_dashboard.md) shows.

## Restore the built-in page

```powershell
python set_summary_dashboard.py VMWARE VMFolder --restore
```

This puts back the built-in Summary page for the object type. It does not delete the dashboard, which stays under **Dashboards**.

## Updating a dashboard

The Summary tab shows a copy of the dashboard, taken when you bind it. Editing the dashboard later does not change the Summary tab. Run the script again with the same name and UUID to publish the update. The new copy replaces the old one.

## Things to know

- **The calls are internal to VCF Operations.** There is no public API for this, so the script uses the same requests as the UI. They can change between VCF Operations releases. The script was written and tested on VCF Operations 9.1.1. Check it on your version before you use it in a script.
- **The script binds by name and UUID.** If the dashboard has been deleted or renamed, the bind fails or binds nothing. Check the name and UUID on **Dashboards** first.
- **Binding is not checked for the object type before it writes.** Check the kind key with the listing in step 1.
- **Object types other than the VMware ones are not tested.** The script takes any adapter kind, but the folder table and tests here are for `VMWARE`.

## See also

- [Summary Dashboard Script](../../tools/summary_dashboard/summary_dashboard.md): the script, its functions and its limits.
- [Customization](customization.md): choose what each Adapter Instance collects, so the dashboard shows the data you need.
- [vSphere Cluster Capacity 2.0 Dashboard](../user-guide/vsphere-cluster-capacity-dashboard.md): an example of a dashboard this pack provides.
