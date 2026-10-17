# Adapter Instance

Once the **VCF Operations vCommunity Management Pack** has been installed and the [policy](policy.md) is set, create an Adapter Instance to connect to your vCenter Server(s).

**On this page:**

- [1. Creating the Adapter Instance](#1-creating-the-adapter-instance)
- [2. Advanced Settings](#2-advanced-settings-optional)
- [3. Validate the Configuration](#3-validate-the-configuration)

---

## 1. Creating the Adapter Instance

Follow these steps within VCF Operations:

1. Navigate to **Administration** → **Integrations** → **Repository** tab.
2. Click on the **"VCF Operations vCommunity"** tile.
3. Click **"Add Account"**.

### 1.1. Account Details

Provide the required information in the fields:

| Field | Description | Important Note |
| :--- | :--- | :--- |
| **Name** | A descriptive name for your Adapter Instance. | E.g., `VCF-Ops-vCenter-Prod` |
| **Description** | A brief description of this instance's purpose. | |
| **vCenter Server** | The **FQDN** or **IP** of your target vCenter Server. | ⚠️ **This must be the exact same FQDN/IP used for your native vCenter Adapter Instance.** The Management Pack matches against it to link its collected objects to the native vSphere topology. |
| **Credential** | Select your vCenter credential and, if needed, your Windows credential. | The Windows credential is only required if you are collecting **Windows Services** and/or **Windows Event Logs**. |
| **Collector/Group** | Select a **Cloud Proxy** (or Collector Group) from the dropdown. | Ensure the Cloud Proxy has connectivity to the vCenter Server. Data collection should begin within 5 minutes. |

### 1.2. Configuration File Selection

The Management Pack uses customizable XML configuration files to define what data to collect. These default files are located under **Infrastructure Operations** → **Configurations** → **Management Pack Configuration** → **System Defined**.

| Field | Configuration File (Default) | Description of Collected Data |
| :--- | :--- | :--- |
| **ESXi Advanced System Settings Config File** | `esxi_advanced_system_settings.xml` | ESXi Advanced System Settings — the specific settings listed in this file (as seen on a host's **Configure** tab in vCenter). |
| **ESXi Software Packages Config File** | `esxi_packages.xml` | Installed VIB/software package details for the package names listed in this file (as seen on a host's **Configure** tab in vCenter). ⚠️ See the [performance note](#a-note-on-esxi-software-packages) below before enabling this in large environments. |
| **VM Advanced Parameters Config File** | `vm_advanced_parameters.xml` | VM Advanced Parameters for the keys listed in this file — visible in the vCenter MOB UI under a VM's `config.extraConfig`. |
| **VM Options Config File** | `vm_options.xml` | VM configuration fields for the property paths listed in this file (e.g. boot options, firmware type) — visible in the vCenter MOB UI under a VM's `config` object. |

> #### A note on ESXi Software Packages
> Retrieving VIB/software package data requires a live RPC call to each host (`fetchSoftwarePackages()`), which is significantly slower than the Management Pack's other, property-collector-based data — this is inherent to how ESXi exposes this data, not something this Management Pack can bypass. In large environments (hundreds of hosts), enabling this can meaningfully add to the total collection time. It's still designed to complete well within a typical collection interval, but if you don't need VIB/driver tracking, leaving `esxi_packages.xml` empty avoids the extra cost entirely.

---

## 2. Advanced Settings (Optional)

You can expand the adapter configuration by clicking **Advanced Settings**.

| Advanced Setting | Default Value | Description |
| :--- | :--- | :--- |
| **Port** | `443` | The port used to connect to vCenter Server. |
| **Cluster Check Period (hours)** | `24` | Length of each [Periodic Cluster Check](../reference/metrics/periodic-cluster-check.md#settings) window, and how often it is calculated: 1, 2, 4, 6, 8, 12 or 24 hours. |
| **Cluster Check Time (UTC)** | `00:00` | Time of day, as HH:MM in UTC, when a Periodic Cluster Check window ends. With a shorter period, the other windows end every period from it. An empty or invalid value uses `00:00`. |
| **Cluster Check Worst Percent** | `5` | Each [Periodic Cluster Check](../reference/metrics/periodic-cluster-check.md#worst) window is summarised by its worst end: this share of the worst samples is ignored. 0 is the single worst sample. 0 to 50. |
| **Monster VM CPU (% of host cores)** | `50` | A VM is a CPU monster when its vCPUs are more than this share of its host's physical cores. Used by [Cluster Risk](../reference/metrics/cluster-risk.md#when-a-vm-is-a-monster). 1 to 100. |
| **Monster VM Memory (% of host DRAM)** | `40` | A VM is a memory monster when its memory is more than this share of its host's DRAM, or the minimum below, whichever is smaller. 1 to 100. |
| **Monster VM Memory Minimum (GB)** | `256` | The memory that qualifies a VM as a memory monster on any host, however large. On a host where the % of host DRAM is smaller, a smaller VM already qualifies. |
| **Windows Service Configuration File** | `windows_service_list.xml` | File used to define which Windows Services to monitor. (Location: System Defined configurations) |
| **Guest OS Service Monitoring Status** | `Disabled` | Toggles Windows Service monitoring using the `windows_service_list.xml` file. Set to `Enabled` to activate. |
| **Windows Event Log Configuration File** | `windows_event_list.xml` | File used to define which Windows Event Log IDs to monitor. (Location: System Defined configurations) |
| **Windows Event Log Monitoring Status** | `Disabled` | Toggles Windows Event Log monitoring using the `windows_event_list.xml` file. Set to `Enabled` to activate. |

> #### A note on Guest OS monitoring
> Both Guest OS features are **agentless**, using GuestAPI with the credentials you provide — but they still add load to both VCF Operations and the target Windows guest, proportional to how many VMs you enable this for. Before enabling either of these across hundreds of Windows machines, evaluate the additional load in your environment and consider a targeted `vm_advanced_parameters`-style scoped rollout (see [Customization](customization.md)) rather than enabling it globally on day one.

---

## 3. Validate the Configuration

1. Click **Validate Connection** to validate the Adapter Instance connection.

Once completed, your Management Pack will now be configured and will begin collecting data.

---

**Next:** [Customization](customization.md): choose what each Adapter Instance collects.
