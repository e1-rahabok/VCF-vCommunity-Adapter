# Content Folder

`Management Pack/content/` holds the objects that VCF Operations imports from the pack: dashboards, reports, super metrics, alert and symptom definitions, and the configuration files that choose what the adapter collects. These are not Python. The pack's code does not build them, it only reads one of the folders at runtime.

Code: [`Management Pack/content/`](../../Management%20Pack/content/)

## What is in it

| Folder | Files | What it is | Read by the code? |
| :--- | :--- | :--- | :--- |
| `files/solutionconfig/` | 6 XML | The configuration files that choose what is collected. See below. | **Yes**, at every collection |
| `dashboards/` | 12 JSON, one in a subfolder | Dashboards for VCF Operations, such as vSphere Cluster Performance 2.0 and vSphere Cluster Capacity 2.0. The subfolder "To be used in reports" holds input dashboards for reports. | No, imported when the pack is installed |
| `reports/` | 36 XML | Reports and views, such as ESXi Host Details, Inventory and the Executive Summary. | No, imported when the pack is installed |
| `supermetrics/` | 10 JSON | Super metrics. Some are replaced by the built-in metrics, see [Super metrics replaced by built-in metrics](../reference/metrics-and-properties.md#super-metrics-replaced-by-built-in-metrics). | No, imported when the pack is installed |
| `alertdefs/` | 3 XML and a schema | Alert definitions, such as ESXi Host License Expiring and Windows Service Down. | No, imported when the pack is installed |
| `symptomdefs/` | 2 XML | The symptoms that the alert definitions use. | No, imported when the pack is installed |
| `resources/` | 1 XML | Views of the VIBs in a cluster, such as "nfnic VIB Vendor Distribution". | No |
| `traversalspecs/` | A schema | The schema for the traversal specs, the relations between objects. No traversal spec is shipped yet. | No |
| `customgroups/`, `policies/`, `recommendations/` | none | Empty. Reserved for future content. | No |

The schemas (`.xsd`) are the VCF Operations format of their files. They are kept next to the files they describe, so an edit can be checked against them.

## The configuration files

The six files in `files/solutionconfig/` are the only content the code reads. Each is an XML file whose text is a comma-separated list, such as the names of the settings to collect. Each Adapter Instance names the file to use for each of six settings, and the adapter reads it from VCF Operations under `SolutionConfig/` at every collection:

| Setting on the Adapter Instance | File | What it chooses |
| :--- | :--- | :--- |
| `esxi_adv_settings_config_file` | `esxi_advanced_system_settings.xml` | The ESXi advanced system settings to publish as properties. |
| `esxi_vib_driver_config_file` | `esxi_packages.xml` | The ESXi software packages (VIBs) to publish. |
| `vm_adv_settings_config_file` | `vm_advanced_parameters.xml` | The VM advanced parameters (`.vmx` settings) to publish. |
| `vm_configuration_config_file` | `vm_options.xml` | The VM configuration values to publish. |
| `win_event_config_file` | `windows_event_list.xml` | The Windows event logs to collect from the VMs. |
| `win_service_config_file` | `windows_service_list.xml` | The Windows services to check in the VMs. |

The file names above are the ones shipped in this folder. An Adapter Instance can name another file that is in VCF Operations, so one vCenter can collect a different standard from another. See [Customization](../configuration-guide/customization.md), which explains how to write and choose them.

**Why it is designed this way:** the standard of settings a company wants is a choice of the company, not of the code. Keeping it in files lets one pack serve many standards, and lets each Adapter Instance have its own, without a new release.

## How it is packaged

The Management Pack Builder (`mp-build`, in the SDK) includes these folders in the `.pak` file when it builds it. When the pak is installed, VCF Operations imports the dashboards, reports, super metrics, alert and symptom definitions and resources. The configuration files stay in VCF Operations, where the code reads them. See [SDK](sdk.md).

## Where the pak's files sit on the appliance

Found on the test appliance (`vcf-m02-ops01`) by listing its folders. The VCF Operations version of that appliance is not recorded here, so check the paths on another version before relying on them.

| Path | What is there |
| :--- | :--- |
| `/usr/lib/vmware-vcops/tomcat-web-app/webapps/ui` | The VCF Operations UI web app. The pack's icons go under `images/adpknd/` and `images/resknd/custom/`, and its content pack under `ContentPack/`. |
| `/usr/lib/vmware-vcops/user/plugins/inbound/vCommunity.conf` and `vCommunity/` | The pack's inbound plugin configuration and its adapter kind image. |
| `/usr/lib/vmware-vcops/tomcat-enterprise/webapps` | Holds `ROOT`, `suite-api`, `telemetry` and `vrops-unicorn`. It does not hold the UI. |

The path `/usr/lib/vmware-vcops/tomcat-enterprise/webapps/vcops-web-ent` that older documents give does not exist on this appliance. Text Widget Content entries are stored in the VCF Operations database, not in a folder, so no path holds them. See [Text Display Widget](../reference/text-display-widget.md).

Do not edit the files in these folders by hand. A manual change may be lost at the next install or upgrade.

## Limitations

- **The content is exported from VCF Operations, so it is not hand-written.** Editing the JSON or XML by hand is fragile. The safe way is to change the object in the VCF Operations UI, export it, and replace the file.
- **Installing a new version imports its content again.** Before an upgrade, check what the import replaces if you edited a copy of a dashboard or report in VCF Operations.
- **A bad configuration file loses only its own data.** A file that is missing, or is not valid XML, gives nothing for that file. The rest of the collection goes on. The problem is shown as a warning event named "vCommunity configuration" on the vCenter object, and the event clears when the file is fixed. See [Configuration files](../troubleshooting-guide/configuration-files.md).
- **The configuration files are read at each collection.** A change takes effect at the next cycle, with no restart.
