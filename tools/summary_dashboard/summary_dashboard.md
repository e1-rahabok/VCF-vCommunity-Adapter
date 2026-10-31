# Summary Dashboard Script

`set_summary_dashboard.py` replaces the built-in **Summary** tab of one object type with a dashboard. It does the same as **Manage Summary Dashboards** in the VCF Operations UI, through the same undocumented UI calls, so you don't have to click through the dialog for each object type.

It changes VCF Operations: the Summary tab of the object type shows the dashboard from then on. `--restore` puts back the built-in page.

## Files

| File | What it is |
| :--- | :--- |
| `set_summary_dashboard.py` | The script. Its function `set_summary_dashboard(ui, adapter_kind, resource_kind, dashboard_name, dashboard_uuid)` is the reusable call. |
| `ui_client.py` | The UI session client it uses. It is adapted from the [vcf-content-factory](https://github.com/sentania-labs/vcf-content-factory) project by Scott Bowe ([LinkedIn](https://www.linkedin.com/in/scottrbowe/)), MIT licensed. The acknowledgment and the copyright notice are at the top of the file. |

## Acknowledgment

This tool would not exist without Scott Bowe's work. He mapped the VCF Operations UI calls that bind Summary tab dashboards, and published the findings and client code in [sentania-labs/vcf-content-factory](https://github.com/sentania-labs/vcf-content-factory). Thank you, Scott. Profile: [linkedin.com/in/scottrbowe](https://www.linkedin.com/in/scottrbowe/).

## Requirements

- Python 3 with the `requests` library.
- An account that can manage dashboards on the instance. The script logs in with the same username and password as the UI, so the local `admin` account works.
- A dashboard on the instance, which can be new: create it in the UI, or import its JSON file. The script binds an existing dashboard by name and UUID. It does not create or import dashboards.

## Running it

Set the connection in the environment, then run the script from `tools/summary_dashboard`:

```powershell
$env:VCFOPS_HOST = '10.115.1.81'
$env:VCFOPS_USER = 'admin'
$env:VCFOPS_PW   = '...'
python set_summary_dashboard.py VMWARE VMFolder ". Object Summary Page for Folder" d22b04d0-1eb2-496e-8944-a143e94187d5
```

It prints the Summary tab as the instance reports it afterwards, for example `{'tabId': '...', 'isDashboard': True}`.

To put back the built-in page:

```powershell
python set_summary_dashboard.py VMWARE VMFolder --restore
```

The dashboard's UUID is in `Dashboards`, or in the `id` field of the dashboard's JSON export.

Every change creates a new copy of the dashboard for the object type. Editing the source dashboard later does not change the Summary tab. Run the script again to publish an update.

## Folder is not one object type

The VMware adapter has **five** folder kinds, and all five have "Folder" in their name. The Summary tab is set per kind, not per "Folder". Bind the wrong one and the page you meant to change does not change.

| Object type in the UI | Resource kind key | Resource kind id |
| :--- | :--- | :--- |
| Virtual Machine Folder | `VMFolder` | `002006VMWAREVMFolder` |
| Datastore Folder | `DatastoreFolder` | `002006VMWAREDatastoreFolder` |
| Host Folder | `HostFolder` | `002006VMWAREHostFolder` |
| Network Folder | `NetworkFolder` | `002006VMWARENetworkFolder` |
| Folder | `Folder` | `002006VMWAREFolder` |

The plain `Folder` kind is not the Virtual Machine Folder. An object's Summary panel shows its object type (for example `Object Type: Virtual Machine Folder`), and the object type is the name to match. When you're not sure which kind to use, list the kinds first:

```python
from ui_client import VCFOpsUIClient
with VCFOpsUIClient(host, user, password, verify_ssl=False) as ui:
    for e in ui.get_resource_kind_list("VMWARE")["resourceKindList"]:
        if "folder" in e["name"].lower():
            print(e["resourceKind"], e["name"], e["resourceKindId"], e["resourceKindTemplate"])
```

Use the `resourceKind` key that matches the object type on the Summary panel, and check the Summary tab of one object of that type afterwards.

Binding `Folder` by mistake is not harmful, because `--restore` puts it back. It is still easy to miss, because the object you looked at was not affected.

## Limits

- The calls are internal to the UI and can change between VCF Operations releases. This tool was written against 9.1.1.
- A dashboard bound to an object type is copied into a Summary template. Per the factory's notes, binding again replaces that copy on the server. Editing the source does not update it.
- The script does not check that the resource kind exists before it writes. Only `--restore` looks the kind up first. Check the kind with the listing above before you bind.

## See also

- [`ui_client.py`](ui_client.py): the calls, with the request forms for each build.
- [Restart Script](../restart/restart.md): restarts the pack's collection, unrelated to Summary tabs.
