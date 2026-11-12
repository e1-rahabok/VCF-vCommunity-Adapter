# Summary Dashboards

Every object in VCF Operations has a **Summary** tab, which shows the built-in summary page for its object type. You can replace that page with a dashboard for a whole object type, for example a dashboard that shows the settings this pack collects.

For one object type, use **Manage Summary Dashboards** in the UI. For several, use the script described on this page. It makes the same calls as the UI, so the result is the same.

## The Summary dashboards in the pack

The pack ships six Summary dashboards. They are installed switched off, and the install does not bind them to their object types, so the Summary tabs keep the built-in page until you bind them.

| Object type in the UI | Resource kind key | Dashboard name | UUID in the pack |
| :--- | :--- | :--- | :--- |
| Virtual Machine Folder | `VMFolder` | `. Object Summary Page for VM Folder` | `d22b04d0-1eb2-496e-8944-a143e94187d5` |
| Host Folder | `HostFolder` | `. Object Summary Page for Compute Folder` | `7e3e9266-b325-4225-b2ad-9198b801ff43` |
| Datastore Folder | `DatastoreFolder` | `. Object Summary Page for Storage Folder` | `9c6b664a-04af-4271-a2ac-23795bfe0365` |
| Network Folder | `NetworkFolder` | `. Object Summary Page for Network Folder` | `6740d93c-c8c3-4189-8bcb-7436da044fff` |
| Distributed Port Group | `DistributedVirtualPortgroup` | `. Object Summary Page for Distributed Port Groups` | `f0a8e1da-6b23-4cc7-8392-37a44162db52` |
| Distributed Switch | `VmwareDistributedVirtualSwitch` | `. Object Summary Page for Distributed Switch` | `4a295d27-a93d-4011-bf18-0bb70b0cbe86` |

The UUIDs are the `id` fields in `Management Pack/content/dashboards/<resource kind>/dashboard.json`. Check them under **Dashboards** on your instance before you bind, as described below. For contributors, binding at install time is described in [Pak Summary Binding](../development-guide/pak-summary-binding.md).

## Before you start

- You need the dashboard on the instance. For your own dashboard, create it in the UI or import its JSON file from the **...** menu on **Dashboards**. The script does not create or import dashboards. It binds an existing dashboard by name and UUID.
- To list the dashboards and their UUIDs, run this from `tools/summary_dashboard`:

  ```python
  from ui_client import VCFOpsUIClient
  with VCFOpsUIClient(host, user, password, verify_ssl=False) as ui:
      for d in ui.list_dashboards():
          print(d["id"], "|", d["name"])
  ```

- You need Python 3 with the `requests` library, and a local account that can manage dashboards, such as `admin`. The script logs in with local accounts only.
- The script is in [`tools/summary_dashboard/`](../../tools/summary_dashboard/). Its reference page is [Summary Dashboard Script](../../tools/summary_dashboard/summary_dashboard.md).

## Step 1: find the object type

Open an object and read **Object Type** on its Summary panel. Use that object type, not the type of a parent object.

Most object types map to one resource kind. Folders are the exception, see the next section.

To list the resource kinds of an adapter, with their current Summary assignment, run this from `tools/summary_dashboard`:

```python
from ui_client import VCFOpsUIClient
with VCFOpsUIClient(host, user, password, verify_ssl=False) as ui:
    for e in ui.get_resource_kind_list("VMWARE")["resourceKindList"]:
        print(e["resourceKind"], "|", e["name"], "|", e["resourceKindId"], "|", e["resourceKindTemplate"])
```

`name` is the object type as the UI shows it. `resourceKind` is the key the script takes. `resourceKindTemplate` is what the Summary tab shows now: `Summary Detail` is the built-in page.

## Folders are five object types

The VMware adapter has five folder kinds, and each one has its own Summary tab. Binding one does not change the others.

| Object type in the UI | Resource kind key |
| :--- | :--- |
| Virtual Machine Folder | `VMFolder` |
| Host Folder | `HostFolder` |
| Datastore Folder | `DatastoreFolder` |
| Network Folder | `NetworkFolder` |
| Folder | `Folder` |

The plain `Folder` kind is not the Virtual Machine Folder. Check the object type on the Summary panel before you choose the key. If you bind the wrong kind, the object you looked at does not change, and `--restore` undoes the binding.

## Step 2: bind the dashboard

From `tools/summary_dashboard`, set the connection in the environment and run the script with the exact dashboard name and its UUID:

```powershell
$env:VCFOPS_HOST = 'vcfops.example.com'
$env:VCFOPS_USER = 'admin'
$env:VCFOPS_PW   = '...'
python set_summary_dashboard.py VMWARE VMFolder ". Object Summary Page for VM Folder" d22b04d0-1eb2-496e-8944-a143e94187d5
```

The script prints the Summary tab as the instance reports it afterwards:

```
VMWARE:VMFolder summary tab now: {'tabId': '...', 'isDashboard': True}
```

`isDashboard: True` means the object type now shows the dashboard.

Don't store the password in a file or in your shell history. Set it for the session only, or prompt for it.

## Step 3: check the result

Open an object of that type and open its **Summary** tab. It shows the dashboard instead of **Recommended Actions** and the built-in charts.

To read the template back with the script's functions, see [Summary Dashboard Script](../../tools/summary_dashboard/summary_dashboard.md).

## Restore the built-in page

```powershell
python set_summary_dashboard.py VMWARE VMFolder --restore
```

This puts back the built-in Summary page for the object type. The dashboard itself stays under **Dashboards**.

## Updating a dashboard

Binding copies the dashboard into a Summary template. Later edits to the dashboard don't change the Summary tab. To publish an edit, run the script again with the same name and UUID. Each run makes a new copy. According to the notes in `ui_client.py`, the same call deletes the object type's previous copy. This has not been checked on an instance.

If you bind a dashboard right after an install or import, the copy can keep an unresolved state and show `Section` headings. See [Dashboards After an Install](../troubleshooting-guide/dashboards-after-install.md).

## Limitations

- The calls are internal to VCF Operations. There is no public API for this, so the script uses the same requests as the UI, and they can change between releases. The script was written and tested on VCF Operations 9.1.1. Test it on your version first.
- The script binds by name and UUID. If the dashboard was deleted or renamed, the bind fails or binds nothing. Check the name and UUID under **Dashboards** first.
- The script does not check that the resource kind exists before it writes. Check the key with the listing in Step 1.
- Only the `VMWARE` adapter kinds are tested. The script accepts any adapter kind.

## See also

- [Summary Dashboard Script](../../tools/summary_dashboard/summary_dashboard.md): the script, its functions and its limits.
- [Included Content](../user-guide/included-content.md): the other dashboards in the pack.
- [Customization](customization.md): choose what each Adapter Instance collects, so the dashboard has the data it needs.

---

**Next:** [TLS and Security Settings](tls-and-security.md)
