# Content Folder

`Management Pack/content/` holds what VCF Operations imports from the pack: dashboards, reports and views, super metrics, alert and symptom definitions, and the configuration files that decide what the adapter collects. None of it is Python. The code reads only one folder, `files/solutionconfig/`, and only through VCF Operations.

Code: [`Management Pack/content/`](../../Management%20Pack/content/)

## What is in it

| Folder | Files | What it is | Read by the code? |
| :--- | :--- | :--- | :--- |
| `files/solutionconfig/` | 6 XML | The configuration files that decide what is collected. See below. | **Yes**, every collection cycle |
| `dashboards/` | 19 JSON | 12 dashboards at the top level, such as vSphere Cluster Performance 2.0 and vSphere Cluster Capacity 2.0. `To be used in reports/` holds one file with the input dashboards of the VCF Optimization Assessment reports. Six folders named after an object type (`VMFolder`, `HostFolder`, `DatastoreFolder`, `NetworkFolder`, `DistributedVirtualPortgroup`, `VmwareDistributedVirtualSwitch`) hold the Summary dashboards for those object types. | No, imported at install |
| `reports/` | 42 XML | Reports and views, such as ESXi Host Details, VM Outdated Hardware Version, and the VCF Optimization Assessment (VOA) reports. A view must never use the id of a built-in view: see [View ids](#view-ids). | No, imported at install |
| `supermetrics/` | 2 JSON | CPU Usable Capacity Utilization and Number of VM. Other super metrics have been replaced by metrics in the code, see [Super metrics replaced by built-in metrics](../reference/metrics-and-properties.md#super-metrics-replaced-by-built-in-metrics). | No, imported at install |
| `alertdefs/` | 4 XML and a schema | Collection Warnings, ESXi Host License Expiring, ESXi Host NIC Disconnected and Windows Service Down. Collection Warnings defines its symptom inline. | No, imported at install |
| `symptomdefs/` | 2 XML | The symptoms used by the NIC Disconnected and Windows Service Down alerts. | No, imported at install |
| `resources/` | 1 XML | Views of the VIBs in a cluster, such as "nfnic VIB Vendor Distribution". | No |
| `traversalspecs/` | A schema | The schema for traversal specs, which define relations between objects. The pack ships no traversal spec. | No |
| `customgroups/`, `policies/`, `recommendations/` | none | Empty, kept for future content. | No |

The schemas (`.xsd`) describe the VCF Operations format of the files next to them, so an edited file can be checked against its schema.

Some content ships turned off:

- **The four alerts** are deactivated in the base policy (`disableInBasePolicy="true"`). Activate them in the policy to use them.
- **The six Summary dashboards** are disabled, and the install does not bind them to the Summary tab. Bind them with the script described in [Summary Dashboards](../configuration-guide/summary-dashboards.md). [Pak Summary Binding](pak-summary-binding.md) explains why the pak can't do this yet.
- **The VOA input dashboards** are disabled. Some are also hidden. They exist to feed the reports.

## The configuration files

The six files in `files/solutionconfig/` are the only content the code reads. Each Adapter Instance names one file for each of six settings. At every collection the adapter reads the named file from VCF Operations, at `SolutionConfig/<name>.xml`. The setting holds the name without `.xml`.

| Setting on the Adapter Instance | Default file | What it lists | Shipped content |
| :--- | :--- | :--- | :--- |
| `esxi_adv_settings_config_file` | `esxi_advanced_system_settings.xml` | ESXi advanced system settings to publish as properties | Every entry commented out |
| `esxi_vib_driver_config_file` | `esxi_packages.xml` | ESXi software packages (VIBs) to publish | Every entry commented out |
| `vm_adv_settings_config_file` | `vm_advanced_parameters.xml` | VM advanced parameters (`.vmx` settings) to publish | Every entry commented out |
| `vm_configuration_config_file` | `vm_options.xml` | vSphere property paths of the VM to publish, such as `config.flags.diskUuidEnabled` | Every entry commented out |
| `win_event_config_file` | `windows_event_list.xml` | Windows event logs and Event IDs to collect from the VMs | Six Event IDs in the Application, Security, Setup and System logs |
| `win_service_config_file` | `windows_service_list.xml` | Windows services to check in the VMs | Every entry commented out |

Five of the files are comma-separated lists inside one XML element. The event list is structured XML, passed to the guest as it is.

An Adapter Instance can name any file that exists in VCF Operations, so each vCenter can collect its own standard. The usual way is to clone a default file and edit the clone. See [Customization](../configuration-guide/customization.md).

Which settings to check is each company's decision. Keeping them in files lets one pack serve many standards, and gives each Adapter Instance its own list without a new release.

## View ids

VCF Operations identifies a view by its id. A view in the pack that has the id of a built-in view replaces the built-in view at install, and deletes it at uninstall. When you add a view, build it as a new view, or export a copy and give it a new id (any UUID version 4). Never keep the id of an exported built-in view. When a view is defined in more than one file, such as the `View - Set` files and `View - Collection01.xml`, every copy has the same id and the same content.

A dashboard that should show an unchanged built-in view names the built-in view's id in `viewDefinitionId` and the pack ships no `ViewDef` for it. `tests/test_view_ids.py` fails if a `ViewDef` has one of the 120 built-in ids (the 117 that earlier versions shipped, and three that this repository added), or if copies of one view differ. The history is in [Upgrade From a Version That Shipped Built-in View Ids](../installation-guide/installation.md#upgrade-from-a-version-that-shipped-built-in-view-ids).

## How it is packaged

The Management Pack Builder (`mp-build`, part of the SDK) includes these folders in the `.pak` file. When the pak is installed, VCF Operations imports the dashboards, reports and views, super metrics, alert and symptom definitions, and resources. The configuration files are stored in VCF Operations, where the code reads them. See [The SDK](sdk.md).

`mp-build` changes the layout of `dashboards/`: it moves each loose file into a subfolder of its own. See [Pak Summary Binding](pak-summary-binding.md#what-mp-build-does-with-contentdashboards).

## Where the pak's files sit on the appliance

These paths were seen on a VCF Operations appliance. Its version was not recorded, so check them on your version before you rely on them.

| Path | What is there |
| :--- | :--- |
| `/usr/lib/vmware-vcops/tomcat-web-app/webapps/ui` | The VCF Operations UI web app. The pack's icons go under `images/adpknd/` and `images/resknd/custom/`, and its content pack under `ContentPack/`. |
| `/usr/lib/vmware-vcops/user/plugins/inbound/vCommunity.conf` and `vCommunity/` | The pack's inbound plugin configuration and its adapter kind image. |
| `/usr/lib/vmware-vcops/tomcat-enterprise/webapps` | `ROOT`, `suite-api`, `telemetry` and `vrops-unicorn`. The UI is not here. |

Older documents give `/usr/lib/vmware-vcops/tomcat-enterprise/webapps/vcops-web-ent` as a path, but it did not exist on that appliance. Text Widget Content entries are stored in the VCF Operations database, not in a folder. See [Text Display Widget](../reference/text-display-widget.md).

Don't edit files in these folders by hand. A manual change can be lost at the next install or upgrade.

## Limitations

- **The content files are exports from VCF Operations.** Editing the JSON or XML directly is fragile. Change the object in the VCF Operations UI, export it, and replace the file.
- **Installing a new version imports the content again.** If you edited a dashboard or report in VCF Operations, check what the import replaces before you upgrade.
- **A bad configuration file loses only its own data.** A file that is missing, unreadable or not valid XML gives nothing for that file, and the rest of the collection goes on. The problem appears as a warning event starting with `vCommunity configuration:` on the vCenter object, and clears a few cycles after the file is fixed. See [Configuration files](../troubleshooting-guide/configuration-files.md).
- **A misspelt path in `vm_options.xml` is worse.** Its entries are added to the VM collector's vSphere read, and an invalid path makes the whole read fail. No VM data is published for that cycle.
- **The configuration files are read every cycle.** A change takes effect at the next cycle, with no restart.
