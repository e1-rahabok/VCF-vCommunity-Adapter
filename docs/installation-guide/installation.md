# Installation

**On this page:**

- [Get the PAK file](#get-the-pak-file)
- [Enable Unsigned PAK Installation](#enable-unsigned-pak-installation)
- [Install the Management Pack](#install-the-management-pack)
- [Create the Adapter Instance](#create-the-adapter-instance)
- [After an Upgrade: Restart Collection](#after-an-upgrade-restart-collection)
- [Upgrade From a Version That Shipped Built-in View Ids](#upgrade-from-a-version-that-shipped-built-in-view-ids)

---

## Get the PAK file

Download `vCommunity_<version>.pak` from the [Releases](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/releases) page. Each release from 0.8.1 on has the validated `.pak` file attached.

## Enable Unsigned PAK Installation

The `.pak` file is not signed by VMware or Broadcom, because this is a community project (see the [README](../../README.md)). Allow unsigned PAK files once per VCF Operations instance:

1. Open `https://<VCF_Ops>/admin` and go to **Administrator Settings** > **Security Settings**.
2. Turn on **Activate Unsigned PAK Installation**.

The installation wizard then shows the **Ignore the PAK file signature checking** checkbox.

## Install the Management Pack

1. Go to **Administration** > **Integrations** > **Repository** and click **Add**.
2. Browse to the `vCommunity_<version>.pak` file and select:
   - **Install the PAK file even if it is already installed**, to upgrade or reinstall over an existing version.
   - **Ignore the PAK file signature checking**. This is required because the pack is unsigned.

   Upload the file and click **Next**.
3. Accept the End User License Agreement and click **Next**.
4. When the installation completes, click **Finish**.

The pack appears on the **Repository** tab as **VCF vCommunity Adapter**. Click it to open its **Management Pack Details**:

![Management Pack Details of VCF vCommunity Adapter: Overview](images/management-pack-details-overview.png)

- **Metrics** lists the metrics and properties the pack adds to each object type, under **vCommunity**:

  ![Management Pack Details: Metrics of Cluster Compute Resource](images/management-pack-details-metrics.png)

- **Content** lists what the pack installs: dashboards, views, reports, alerts, super metrics and configuration files:

  ![Management Pack Details: Content, Configuration Files](images/management-pack-details-content.png)

Some of this content is off after the install. [Included Content](../user-guide/included-content.md) lists what to turn on.

## Create the Adapter Instance

Installing the pack does not start collection. Create an Adapter Instance for each vCenter, as described in [Adapter Instance](../configuration-guide/adapter-instance.md).

## After an Upgrade: Restart Collection

After you install a new version over an existing one, the existing Adapter Instances can stop collecting. The install reports success, but under **Administration** > **Integrations** > **Accounts** the instance under **VCF vCommunity Adapter** shows **Warning**, its state is `Failed`, and it does not recover by itself. This has happened on several upgrades of the pack. The cause is not known, and it is not listed as a known issue in Broadcom's documentation.

To fix it, do this for each Adapter Instance of the pack:

1. Under **Administration** > **Integrations** > **Accounts**, expand **VCF vCommunity Adapter**.
2. Open the **⋮** menu next to the Adapter Instance and choose **Stop Collecting**.
3. Open the same menu again and choose **Start Collecting**.
4. Wait for the next collection cycle, about 5 minutes. The status changes to **Collecting**, and the tooltip shows **Status: Data receiving**.

Data collected before the upgrade is kept. The time between the install and the restart is a gap in the metrics.

Contributors can restart every Adapter Instance of the pack with one script: see [Restart Script](../../tools/restart/restart.md).

## Upgrade From a Version That Shipped Built-in View Ids

Versions 0.1.5 to 0.8.1 shipped views under the ids of views that are built into VCF Operations: 41 in the released 0.1.5 pak, 117 in 0.1.6 to 0.3.1, and 120 in 0.4.2 to 0.8.1 (three more). (Versions before 0.1.5 shipped no view with one of these ids.) VCF Operations matches a view by its id, so installing the pack replaced the built-in view with the pack's copy, and uninstalling the pack deleted the view. Stock dashboards and reports that use a built-in view then showed "The view does not exist". This version does not ship those ids:

- 19 views that were identical to the built-in view, or differed only in title, description or an explicit default value, are no longer shipped. The pack's dashboards use the built-in view.
- The other 98 views have new ids. They are the pack's own views, and they keep their names.
- This repository added three more views, VCF Management Services Nodes View, Volumes View and Components View, under ids of views that are built into 9.1.1. They are not among the 117, and they are not present in an 8.18.7 content export. They have new ids too. Components View is identical to the built-in view of 9.1.1, but it is not dropped, so the pack's dashboard keeps its own copy of it on every version.

A fresh install of this version, and its uninstall, do not touch built-in views. An instance that had one of the older versions is different. What happens when you upgrade it depends on the VCF Operations version:

| VCF Operations | What the upgrade does |
| :--- | :--- |
| 9.0.2 and 9.1.1 | The platform removes content that the new version no longer ships, so **the upgrade deletes all 117 built-in views** that the old version had overwritten, about a minute after the import. That includes the 19 that this version no longer ships. On 9.1.1 the same rule is expected to delete the three VCF Management Services built-in views as well (expected, not measured). The pack's views with the new ids are added. |
| 8.18.7 | The upgrade deletes nothing. The old version's modified copies stay under the built-in ids, so **the built-in views stay replaced**. 75 of the new views get " 1" added to their title, because the old and the new copy have the same title. A later uninstall of the pack deletes the old copies too: 249 views in the measurement, the 160 new ones and 89 under built-in ids. |

Do not uninstall the pack to clear the duplicate titles on 8.18.7. That deletes the views under the built-in ids, which is the problem described above.

The pack's own dashboards are affected on 9.0.2 and 9.1.1 as well. Until the built-in views are restored, the widgets that use one of the 19 views that are no longer shipped also show "The view does not exist". In this version that is 11 widgets in five dashboards: VM Capacity 2.0 (3), vSphere Cluster Performance 2.0 (3), vSphere Network Configuration 2.0 (2), vSphere Cluster Capacity 2.0 (1), and the input dashboard in `To be used in reports/` (2), which the VCF Optimization Assessment reports use.

These results were measured with the 0.3.1 release of the original pack, which shipped the same 117 ids, on 8.18.7, 9.0.2 and 9.1.1 with no Adapter Instance configured. They were not measured with a `.pak` file built from this repository.

**Restore the built-in views.** Import the view definitions from a content export of a clean instance of the same VCF Operations version, one that never had the pack installed. Export the views from that instance, then import the file into your instance. An export taken from the affected instance does not help, because it contains the pack's copies. This was tested with 0.3.1 on 8.18.7, 9.0.2 and 9.1.1, after an uninstall, and on 9.0.2 and 9.1.1 also after an upgrade. On 8.18.7 the import overwrites the old copies that stayed behind. A 9.1.1 export also holds the three VCF Management Services views, so the same import should restore them (not measured). Two cautions:

- Importing a full view export overwrites any edits you made to built-in views. Import only the views that are missing when you can.
- Not tested: on 8.18.7, whether views restored this way are deleted again by a later uninstall of the pack. After any later uninstall, check the built-in views and import them again if they are gone.

---

**Next:** [Policy](../configuration-guide/policy.md), then [Adapter Instance](../configuration-guide/adapter-instance.md).
