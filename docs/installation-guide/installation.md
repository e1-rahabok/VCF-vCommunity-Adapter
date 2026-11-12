# Installation

**On this page:**

- [Get the PAK file](#get-the-pak-file)
- [Enable Unsigned PAK Installation](#enable-unsigned-pak-installation)
- [Install the Management Pack](#install-the-management-pack)
- [Create the Adapter Instance](#create-the-adapter-instance)
- [After an Upgrade: Restart Collection](#after-an-upgrade-restart-collection)

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

---

**Next:** [Policy](../configuration-guide/policy.md), then [Adapter Instance](../configuration-guide/adapter-instance.md).
