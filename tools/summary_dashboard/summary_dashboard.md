# Summary Dashboard Script

`set_summary_dashboard.py` replaces the built-in **Summary** tab of one object type with a dashboard. It does what **Manage Summary Dashboards** does in the VCF Operations UI, with the same undocumented UI calls, so you don't have to go through the dialog for each object type.

It changes VCF Operations: from then on, the Summary tab of the object type shows the dashboard. `--restore` puts the built-in page back.

For the step-by-step procedure, see [Summary Dashboards](../../docs/configuration-guide/summary-dashboards.md).

## Files

| File | What it is |
| :--- | :--- |
| `set_summary_dashboard.py` | The script. Its function `set_summary_dashboard(ui, adapter_kind, resource_kind, dashboard_name, dashboard_uuid)` is the reusable call. |
| `ui_client.py` | The UI session client the script uses. It is adapted from the [vcf-content-factory](https://github.com/sentania-labs/vcf-content-factory) project by Scott Bowe ([LinkedIn](https://www.linkedin.com/in/scottrbowe/)), under the MIT license. The acknowledgment and copyright notice are at the top of the file. |

## Acknowledgment

This tool is built on Scott Bowe's work. He mapped the VCF Operations UI calls that bind Summary tab dashboards, and published his findings and client code in [sentania-labs/vcf-content-factory](https://github.com/sentania-labs/vcf-content-factory). Thank you, Scott. Profile: [linkedin.com/in/scottrbowe](https://www.linkedin.com/in/scottrbowe/).

## Requirements

- Python 3 with the `requests` library.
- A local VCF Operations account that can manage dashboards, such as `admin`. The client logs in as a local account (`localItem`), so accounts from an identity source such as Active Directory do not work.
- The dashboard on the instance. The script binds an existing dashboard by name and UUID. It does not create or import dashboards.

## The pack's Summary dashboards

The pack installs six Summary dashboards, but the install does not bind them to any object type. Bind each one with the script, using its name and UUID:

| Resource kind key | Dashboard name | UUID |
| :--- | :--- | :--- |
| `VMFolder` | `. Object Summary Page for VM Folder` | `d22b04d0-1eb2-496e-8944-a143e94187d5` |
| `HostFolder` | `. Object Summary Page for Compute Folder` | `7e3e9266-b325-4225-b2ad-9198b801ff43` |
| `DatastoreFolder` | `. Object Summary Page for Storage Folder` | `9c6b664a-04af-4271-a2ac-23795bfe0365` |
| `NetworkFolder` | `. Object Summary Page for Network Folder` | `6740d93c-c8c3-4189-8bcb-7436da044fff` |
| `DistributedVirtualPortgroup` | `. Object Summary Page for Distributed Port Groups` | `f0a8e1da-6b23-4cc7-8392-37a44162db52` |
| `VmwareDistributedVirtualSwitch` | `. Object Summary Page for Distributed Switch` | `4a295d27-a93d-4011-bf18-0bb70b0cbe86` |

The files are in `Management Pack/content/dashboards/<resource kind key>/dashboard.json`. For any other dashboard, the UUID is in the `id` field of its JSON export.

## Running it

Set the connection in the environment, then run the script from `tools/summary_dashboard`:

```powershell
$env:VCFOPS_HOST = 'vcfops.example.com'
$env:VCFOPS_USER = 'admin'
$env:VCFOPS_PW   = '...'
python set_summary_dashboard.py VMWARE VMFolder ". Object Summary Page for VM Folder" d22b04d0-1eb2-496e-8944-a143e94187d5
```

The script prints the Summary tab as the instance reports it afterwards, for example `{'tabId': '...', 'isDashboard': True}`.

To put back the built-in page:

```powershell
python set_summary_dashboard.py VMWARE VMFolder --restore
```

Don't keep the password in a file or in your shell history. Set it for the session only.

## How the binding works

When you bind a dashboard, the server copies it into a Summary template for the object type. According to the notes in `ui_client.py`, the same call deletes the object type's previous copy, so there is one copy per object type.

Because it is a copy, editing the source dashboard later does not change the Summary tab. Run the script again to publish the change.

## Folder is not one object type

The VMware adapter has five folder kinds, and all of them have "Folder" in their name. The Summary tab is set per kind. If you bind the wrong one, the page you meant to change stays the same.

| Object type in the UI | Resource kind key | Resource kind ID |
| :--- | :--- | :--- |
| Virtual Machine Folder | `VMFolder` | `002006VMWAREVMFolder` |
| Datastore Folder | `DatastoreFolder` | `002006VMWAREDatastoreFolder` |
| Host Folder | `HostFolder` | `002006VMWAREHostFolder` |
| Network Folder | `NetworkFolder` | `002006VMWARENetworkFolder` |
| Folder | `Folder` | `002006VMWAREFolder` |

The plain `Folder` kind is not the Virtual Machine Folder. An object's Summary panel shows its object type, for example `Object Type: Virtual Machine Folder`, and that is the name to match. If you are not sure which kind to use, list the kinds first:

```python
from ui_client import VCFOpsUIClient
with VCFOpsUIClient(host, user, password, verify_ssl=False) as ui:
    for e in ui.get_resource_kind_list("VMWARE")["resourceKindList"]:
        if "folder" in e["name"].lower():
            print(e["resourceKind"], e["name"], e["resourceKindId"], e["resourceKindTemplate"])
```

Use the `resourceKind` key that matches the object type on the Summary panel, and afterwards check the Summary tab of one object of that type. A wrong binding does no harm, and `--restore` undoes it.

## Limits

- The calls are internal to the UI and can change between VCF Operations releases. The tool was written against VCF Operations 9.1.1.
- The script does not check that the resource kind exists before it writes. Only `--restore` looks the kind up first. Check the kind with the listing above before you bind.
- The script connects without checking the instance's TLS certificate (`verify_ssl=False`). Use it on a trusted network.

## See also

- [`ui_client.py`](ui_client.py): the calls, with the request forms for each VCF Operations build.
- [Dashboards After an Install](../../docs/troubleshooting-guide/dashboards-after-install.md): why to bind only after a dashboard has finished loading.
