# Included Content

The pack installs dashboards, views, reports, alerts and super metrics together with the adapter. Some of them work right after the install. Others are off until you turn them on. This page lists what ships and what you have to do for each part.

The files are in [`Management Pack/content/`](../../Management%20Pack/content/). After the install, the pack's **Management Pack Details** list them under **Content** (see [Installation](../installation-guide/installation.md#install-the-management-pack)).

## Summary

| Content | How many | State after install | What to do |
| :--- | :--- | :--- | :--- |
| Dashboards | 12 | On | Nothing. Most need the pack's metrics, so they fill in after the first collection cycles. |
| Summary dashboards | 6 | Off, and not bound | Bind them to their object types, see [Summary Dashboards](../configuration-guide/summary-dashboards.md). |
| VCF Optimization Assessment reports | 16 | Available | Run them against the vSphere World object. |
| VCF Optimization Assessment input dashboards | 34 | Off | Nothing. The reports use them. |
| Views | 189 | Available | Nothing. |
| Alerts | 4 | Off in the base policy | [Turn on the alerts](#turn-on-the-alerts) you want. Three of them need editing first. |
| Super metrics | 2 | Off | [Turn on the super metrics](#turn-on-the-super-metrics) in the policy. |

## Dashboards

The names are as they appear in VCF Operations. The part before `/` is the dashboard folder.

| Dashboard | What it is for |
| :--- | :--- |
| vCommunity/Overall Daily Check | A set of basic daily health checks of the whole environment. |
| vCommunity/vSphere Cluster Capacity 2.0 | Weekly capacity review of the clusters: the three cluster KPIs, their sub-metrics and the Periodic Cluster Check. See [vSphere Cluster Capacity 2.0 Dashboard](vsphere-cluster-capacity-dashboard.md). |
| vCommunity/vSphere Cluster Performance 2.0 | Performance of the vSphere clusters, with both contention and utilization counters. |
| vCommunity/VM Performance 2.0 | Monitoring and troubleshooting of VM performance, focused on the contention metrics. |
| Capacity/VM Capacity (new) | VM capacity, with the hosts' capacity remaining and time remaining. |
| vCommunity/vSphere Cluster Configuration 2.0 | Cluster settings that need attention: wrong settings and outdated components. |
| vCommunity/ESXi Configuration 2.0 | ESXi host settings that need attention. |
| vCommunity/vSphere Network Configuration 2.0 | vSphere network settings that need attention. |
| vCommunity/VM Storage Configuration | VM storage settings that need attention. |
| vCommunity/vSphere Resource Management | Shares and reservations across VMs, resource pools and clusters. |
| vCommunity/Critical Business Applications | Performance and availability of multi-tier business applications. It needs [Business Applications](../configuration-guide/business-applications.md) to be defined. |
| VCF Management Service | Health of the VCF 9.1 Management Service platform. |

The 2.0 dashboards and VM Capacity (new) are new versions of dashboards that VCF Operations already has. They are separate dashboards and don't overwrite the built-in ones.

The six Summary dashboards (`. Object Summary Page for ...`) replace the Summary tab of the four folder types, Distributed Switch and Distributed Port Group. They are listed in [Summary Dashboards](../configuration-guide/summary-dashboards.md#the-summary-dashboards-in-the-pack).

## VCF Optimization Assessment reports

The VCF Optimization Assessment (VOA) is a set of reports for a VCF consultant to walk through with a customer as part of a health review. They are meant to be used together with the performance dashboards, not read on their own. Run them against the vSphere World object to cover the whole environment.

| Kind | Reports |
| :--- | :--- |
| PDF | VOA - Executive Summary, VOA - Inventory, VOA - Configuration, VOA - Capacity, VOA - Performance |
| CSV export | vCenter, vSphere Data Centers, vSphere Clusters, ESXi Hosts, Virtual Machine, Datastores, Distributed Switch, Distributed Port Groups, vSphere Supervisor, vSphere Namespace, vSphere Pod |

The PDF reports are built from the 34 dashboards in the `VCF Optimization Assessment` folder, named `Report: ...`. Those dashboards are switched off so that they don't clutter the dashboard list. Two charts in them still use the super metric **vSphere Clusters not Green**, which the pack no longer ships, so those charts have no data.

## Views

The pack installs 189 views, most of them used by the dashboards and reports. These are useful on their own:

| View | Object type | Shows |
| :--- | :--- | :--- |
| ESXi Host Details vCommunity | Host System | Host details |
| ESXi Host Hardware vCommunity | Host System | Hardware models |
| ESXi Host License Information vCommunity | Host System | Licenses |
| ESXi Host Maintenance Mode vCommunity | Host System | Maintenance state |
| ESXi Host Power State vCommunity | Host System | Power state |
| ESXi Host Versions vCommunity | Host System | ESXi versions |
| ESXi Host NIC Details | Host System | Physical NICs |
| ESXi Packages | Host System | The software packages from your packages configuration file |
| VM Details vCommunity | Virtual Machine | VM details |
| VM Outdated Hardware Version | Virtual Machine | VMs whose hardware version is not 21 or 22 |
| VM Tools not running | Virtual Machine | VMs without running VMware Tools |
| VM Tools outdated | Virtual Machine | VMs with outdated VMware Tools |
| VM with large Snapshot | Virtual Machine | VMs with large snapshots |
| VM with old Snapshots | Virtual Machine | VMs with old snapshots |
| Windows Services vCommunity | Virtual Machine | The Windows services from your service configuration file |
| vSphere Clusters Capacity List | Cluster Compute Resource | Cluster capacity |
| VCF Management Services, and its Nodes, Volumes and Components views | VCF Management Services objects | The VCF Management Service platform |

The hardware versions 21 and 22 in **VM Outdated Hardware Version** are fixed in the view. Edit the view's filter if your standard is different.

## Alerts

All four alerts are off in the base policy. Collection Warnings works as shipped. The other three check one specific license, NIC or service, so they are examples: copy them and change the key to match your environment before you turn them on.

| Alert | Object type | Fires when | Before you turn it on |
| :--- | :--- | :--- | :--- |
| vCommunity Collection Warnings | vCenter adapter instance (the vCenter object) | `vCommunity\|Collection Health\|Warnings in Last Cycle` is above 0. It waits 2 cycles before it fires and 2 cycles before it clears. | Nothing. See [Symptoms](../troubleshooting-guide/symptoms.md#a-collection-warnings-alert-is-shown). |
| ESXi Host License Expiring | Host System | `vCommunity\|Licensing:vSphere 8 Enterprise Plus for VCF\|Remaining Days` is below 160, with a higher severity as the date gets closer. | Change the license name in the key to the one your hosts use. |
| ESXi Host NIC Disconnected | Host System | `vCommunity\|Network\|Device:vmnic0\|Status` is not `Connected`. Critical. | It checks `vmnic0` only. Add symptoms for the other NICs you care about. |
| Windows Service Down | Virtual Machine | `vCommunity\|Guest OS\|Services:DHCP Client\|Service Status` is not `Running`. | It checks the DHCP Client service only. Change or add symptoms for your services. Needs Guest OS Service Monitoring, see [Adapter Instance](../configuration-guide/adapter-instance.md#2-advanced-settings-optional). |

### Turn on the alerts

1. Go to **Administration** > **Configurations** > **Policy Definition** and edit the policy that applies to the objects, for example the **Default Policy**.
2. Open **Alerts and Symptoms**, find the alert by name and set it to **Activated**.
3. Save the policy.

## Super metrics

| Super metric | Object types | What it is |
| :--- | :--- | :--- |
| CPU Usable Capacity Utilization | Cluster Compute Resource | CPU utilization against the usable capacity, which takes the cluster's HA and buffer into account. Percent. |
| Number of VM | Distributed Port Group, Distributed Switch | The number of VMs, running or not, connected to the port group or switch. |

The dashboards use them, so turn them on after the install.

### Turn on the super metrics

1. Go to **Administration** > **Configurations** > **Policy Definition** and edit the **Default Policy** (or the policy that applies to the objects).
2. Open **Metrics and Properties**.
3. Select the object type: **Cluster Compute Resource** for CPU Usable Capacity Utilization, and **Distributed Port Group** and **Distributed Switch** for Number of VM.
4. Filter on `super metric`, set the super metric to **Activated**, and save the policy.

Values appear from the next collection cycle.

## Not included

The pack has no dashboard for Windows services. [Dale Hassinger](https://www.vcrocs.info/vcommunity-mp-windows-servers-services/) has published one.

---

**Next:** [vSphere Cluster Capacity 2.0 Dashboard](vsphere-cluster-capacity-dashboard.md)
