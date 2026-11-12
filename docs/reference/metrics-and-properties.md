# Metrics and Properties

Every metric and property the pack publishes, by object type. All keys start with `vCommunity|`.

A key with a `<placeholder>` segment is instanced: it repeats once per item on the object, such as once per virtual disk or once per VIB package. An object usually has more keys than the rows below.

Some properties come from the configuration files that the Adapter Instance names. The default files ship with every entry commented out, except `windows_event_list.xml`, so those properties appear only after you configure a clone of the file. See [Customization](../configuration-guide/customization.md).

How each metric and KPI is calculated is in [Metrics](metrics/README.md).

**Object types:**

- [Cluster](#cluster)
- [Host](#host)
- [Datastore](#datastore)
- [Virtual Machine](#virtual-machine)
- [vCenter](#vcenter)
- [vSphere World](#vsphere-world)
- [Datacenter](#datacenter)
- [Content Library](#content-library)
- [Library Item](#library-item)
- [VM Template](#vm-template)
- [Business Application objects](#business-application-objects)
- [Events](#events)
- [Super metrics replaced by built-in metrics](#super-metrics-replaced-by-built-in-metrics)

---

## Cluster

| Type | Key | Description |
| :--- | :--- | :--- |
| Metric | `vCommunity\|Availability\|Cluster Operational Availability` | `min(100, (sum of the host values − the k lowest) ÷ (N − k))`, where vSphere HA tolerates k host failures. No failover level counts as N+0. See [Operational Availability](metrics/operational-availability.md#known-limitations). |
| Property | `vCommunity\|Cluster Configuration\|Configuration Status` | vCenter's configuration status of the cluster: green, yellow, red or gray. |
| Metric | `vCommunity\|Cluster Configuration\|Number of Effective Hosts` | Hosts that contribute resources to the cluster. Hosts in maintenance mode are not counted. |
| Property | `vCommunity\|Cluster Configuration\|Overall Status` | vCenter's overall status of the cluster (green, yellow or red), combined from its hosts, DRS and HA. |
| Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Host Monitoring` | Whether vSphere HA host monitoring is enabled. |
| Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Response \ Host Isolation` | What HA does when a host becomes isolated from the network, such as `powerOff`, `shutdown` or `none`. |
| Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Response \ Default VM Restart Priority` | The restart priority (low, medium or high) of VMs restarted after a host failure. |
| Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Response \ Datastore APD` | HA's response when a datastore is in All Paths Down. |
| Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Response \ Datastore PDL` | HA's response when a datastore is in Permanent Device Loss. |
| Property | `vCommunity\|Cluster Configuration\|vSphere HA\|VM Monitoring` | Whether VM Monitoring restarts a VM whose VMware Tools heartbeat stops. |
| Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Heartbeat Datastore` | The policy HA uses to choose heartbeat datastores. |
| Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Failure Interval` | Seconds without a VMware Tools heartbeat before VM Monitoring treats the VM as failed. |
| Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Max Failure Window` | The window, in seconds, in which VM Monitoring allows Max Failures restarts. |
| Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Max Failures` | The number of restarts VM Monitoring allows within the Max Failure Window. |
| Property | `vCommunity\|Cluster Configuration\|vSphere HA\|Minimum Up Time` | Seconds a VM must run after a restart before VM Monitoring watches it again. |
| Property | `vCommunity\|Cluster Configuration\|Distributed Resource Scheduler\|Proactive DRS` | Whether Proactive DRS is enabled. It moves VMs away from hosts with predicted hardware failures. |
| Property | `vCommunity\|Cluster Configuration\|Distributed Resource Scheduler\|Scale Descendants Shares` | Whether the shares of VMs in nested resource pools are scaled. |
| Property | `vCommunity\|Cluster Configuration\|Distributed Resource Scheduler\|CPU Over-Commitment` | The `MaxVcpusPerCore` advanced option: the highest vCPU-to-core ratio DRS allows. |
| Property | `vCommunity\|Cluster Configuration\|Distributed Resource Scheduler\|Virtual Machine Automation Enabled` | Whether DRS allows per-VM automation overrides. |
| Metric | `vCommunity\|Cluster Configuration\|Distributed Resource Scheduler\|DRS Score` | vCenter's DRS Score of the cluster, 0 to 100, higher is better. Published as 0 when DRS is off, or when vCenter reports a negative score. When DRS is off, the DRS properties above read `null`. |
| Property | `vCommunity\|Cluster Configuration\|EVC\|Enabled` | Whether Enhanced vMotion Compatibility (EVC) is enabled. |
| Property | `vCommunity\|Cluster Configuration\|EVC\|Mode` | The EVC mode key of the cluster, such as `intel-cascadelake`. |
| Property | `vCommunity\|Cluster Configuration\|DPM\|Host Power Action Rate` | The Distributed Power Management rate (1 to 5): how quickly DPM powers hosts on and off. Published whenever the cluster has a DPM configuration, whether DPM is on or off. |
| Metric | `vCommunity\|Cluster Performance\|Cluster Performance Score` | KPI, 0 to 100 %, from the 9 sub-metrics below. 100 is best. See [Cluster Performance](metrics/cluster-performance.md). |
| Metric | `vCommunity\|Cluster Performance\|Worst VM CPU Ready` | The highest 20-second peak CPU Ready (%) of the powered-on VMs in the cluster. |
| Metric | `vCommunity\|Cluster Performance\|Worst VM CPU Co-Stop` | The highest 20-second peak CPU Co-Stop (%) of the powered-on VMs in the cluster. |
| Metric | `vCommunity\|Cluster Performance\|Worst VM Memory Latency` | The highest 20-second peak memory contention (%) of the powered-on VMs in the cluster. |
| Metric | `vCommunity\|Cluster Performance\|Worst VM Disk Latency` | The highest 20-second peak virtual disk latency (ms) of the powered-on VMs in the cluster. |
| Metric | `vCommunity\|Cluster Performance\|90th Percentile VM CPU Ready` | The 20-second peak CPU Ready (%) that 90 % of the powered-on VMs are at or below. |
| Metric | `vCommunity\|Cluster Performance\|90th Percentile VM CPU Co-Stop` | The 20-second peak CPU Co-Stop (%) that 90 % of the powered-on VMs are at or below. |
| Metric | `vCommunity\|Cluster Performance\|90th Percentile VM Memory Latency` | The 20-second peak memory contention (%) that 90 % of the powered-on VMs are at or below. |
| Metric | `vCommunity\|Cluster Performance\|90th Percentile VM Disk Latency` | The 20-second peak virtual disk latency (ms) that 90 % of the powered-on VMs are at or below. |
| Metric | `vCommunity\|Cluster Performance\|Highest ESXi Bad Network Packets` | Errored and dropped packets as a % of all packets in the last 5 minutes, on the worst host. Needs Total Packets Received and Transmitted activated in the [policy](../configuration-guide/policy.md). |
| Metric | `vCommunity\|Cluster Risk\|Cluster Risk Score` | KPI, 0 to 100 %, from the 12 sub-metrics below. Higher is worse: red is 75 to 100. See [Cluster Risk](metrics/cluster-risk.md) and its [bands](metrics/cluster-risk.md#bands-red-is-high). |
| Metric | `vCommunity\|Cluster Risk\|Highest ESXi CPU Thread Utilization` | CPU thread utilization (%, `cpu.utilization`) of the busiest host. |
| Metric | `vCommunity\|Cluster Risk\|Worst ESXi CPU Imbalance` | Running CPU threads divided by running CPU cores, on the worst host. 1 is one thread per busy core. 2 is both hyper-threads busy on every busy core. |
| Metric | `vCommunity\|Cluster Risk\|Highest ESXi Memory Consumed` | Consumed memory as a % of host DRAM, on the fullest host. |
| Metric | `vCommunity\|Cluster Risk\|Worst ESXi Memory Ballooned` | Ballooned memory as a % of host DRAM, on the worst host. |
| Metric | `vCommunity\|Cluster Risk\|Worst ESXi Memory Zip Swap` | Compressed plus swapped memory as a % of host DRAM, on the worst host. |
| Metric | `vCommunity\|Cluster Risk\|Worst ESXi Memory Tiering Latency` | Read latency (µs) of the NVMe memory tier, on the worst host. Published only when a host in the cluster has memory tiering. |
| Metric | `vCommunity\|Cluster Risk\|Highest ESXi CPU Reservation` | Reserved CPU as a % of host CPU capacity, on the highest host. |
| Metric | `vCommunity\|Cluster Risk\|Highest ESXi Memory Reservation` | Reserved memory as a % of host DRAM, on the highest host. |
| Metric | `vCommunity\|Cluster Risk\|Highest ESXi CPU Overcommit Ratio` | vCPUs of the powered-on VMs per physical core, on the highest host. |
| Metric | `vCommunity\|Cluster Risk\|Highest ESXi Memory Overcommit Ratio` | Memory of the powered-on VMs per unit of host DRAM, on the highest host. |
| Metric | `vCommunity\|Cluster Risk\|Highest CPU Monster VM to Host Ratio` | vCPUs of the largest powered-on VM against the monster size of its host: by default, half of its physical cores. Above 1, the VM is a monster. See [When a VM is a monster](metrics/cluster-risk.md#when-a-vm-is-a-monster). |
| Metric | `vCommunity\|Cluster Risk\|Highest Memory Monster VM to Host Ratio` | Memory of the largest powered-on VM against the monster size of its host: by default, 40 % of its DRAM or 256 GB, whichever is smaller. Above 1, the VM is a monster. |
| Metric | `vCommunity\|Cluster Consumption\|Cluster Consumption Score` | KPI, 0 to 100 %, of how much of the cluster's usable capacity (Total − HA − Buffer) is consumed, from the 5 sub-metrics below. Higher is worse: red is 75 to 100. See [Cluster Consumption](metrics/cluster-consumption.md). |
| Metric | `vCommunity\|Cluster Consumption\|Cluster-wide ESXi CPU Thread Utilization` | CPU threads in use on all running hosts, as a % of their usable threads. |
| Metric | `vCommunity\|Cluster Consumption\|Cluster-wide ESXi Memory Consumed` | Consumed memory of all running hosts, as a % of their usable DRAM. |
| Metric | `vCommunity\|Cluster Consumption\|Cluster Memory Tiering Consumption` | NVMe memory tier in use on all running hosts, as a % of their usable NVMe tier. Published only when the cluster has memory tiering. |
| Metric | `vCommunity\|Cluster Consumption\|Cluster-wide ESXi Memory Ballooned` | Ballooned memory of all running hosts, as a % of their usable DRAM. |
| Metric | `vCommunity\|Cluster Consumption\|Cluster-wide ESXi Memory Zip Swap` | Compressed plus swapped memory of all running hosts, as a % of their usable DRAM. |
| Metric | `vCommunity\|Periodic Cluster Check\|Worst Cluster Performance` | The low end (%) of Cluster Performance Score over the last window (24 hours by default), ignoring the Cluster Check Worst Percent of the worst samples. Published once per window. See [Worst](metrics/periodic-cluster-check.md#worst). |
| Metric | `vCommunity\|Periodic Cluster Check\|Worst Cluster Risk` | The high end (%) of Cluster Risk Score over the same window, calculated the same way. |
| Metric | `vCommunity\|Periodic Cluster Check\|Worst Cluster Consumption` | The high end (%) of Cluster Consumption Score over the same window, calculated the same way. |
| Metric | `vCommunity\|Periodic Cluster Check\|Close for Business` | 1 when the cluster is full and should take no new VMs. 0 when it is open. See [the rule](metrics/periodic-cluster-check.md#the-rule). |
| Metric | `vCommunity\|Resource Pools\|Number of Resource Pools` | Resource pools of the cluster at levels 1 to 3: directly under the cluster, and up to three levels down. Read from the pools' parents in VCF Operations. |
| Metric | `vCommunity\|Resource Pools\|Cascading Resource Pools` | Resource pools of the cluster at levels 2 to 5, that is, pools under another pool. |

---

## Host

| Type | Key | Description |
| :--- | :--- | :--- |
| Metric | `vCommunity\|Network\|Network Speed Degradation` | Actual NIC speed as a % of the configured speed, over the physical NICs that can be compared. 100 % means no degradation. See [Network Speed Degradation](metrics/network-speed-degradation.md#known-limitations). |
| Metric | `vCommunity\|Availability\|ESXi Host Operational Availability` | 25 % each for powered on, connected, not in maintenance and not in quarantine. Published only for hosts that vCenter reports as connected. See [Operational Availability](metrics/operational-availability.md#known-limitations). |
| Metric | `vCommunity\|ESXi Performance\|ESXi Performance Score` | KPI, 0 to 100 %, from the 9 sub-metrics below. 100 is best. See [ESXi Performance](metrics/esxi-performance.md). |
| Metric | `vCommunity\|ESXi Performance\|Worst VM CPU Ready` | The highest 20-second peak CPU Ready (%) of the powered-on VMs on the host. |
| Metric | `vCommunity\|ESXi Performance\|Worst VM CPU Co-Stop` | The highest 20-second peak CPU Co-Stop (%) of the powered-on VMs on the host. |
| Metric | `vCommunity\|ESXi Performance\|Worst VM Memory Latency` | The highest 20-second peak memory contention (%) of the powered-on VMs on the host. |
| Metric | `vCommunity\|ESXi Performance\|Worst VM Disk Latency` | The highest 20-second peak virtual disk latency (ms) of the powered-on VMs on the host. |
| Metric | `vCommunity\|ESXi Performance\|90th Percentile VM CPU Ready` | The 20-second peak CPU Ready (%) that 90 % of the powered-on VMs on the host are at or below. |
| Metric | `vCommunity\|ESXi Performance\|90th Percentile VM CPU Co-Stop` | The 20-second peak CPU Co-Stop (%) that 90 % of the powered-on VMs on the host are at or below. |
| Metric | `vCommunity\|ESXi Performance\|90th Percentile VM Memory Latency` | The 20-second peak memory contention (%) that 90 % of the powered-on VMs on the host are at or below. |
| Metric | `vCommunity\|ESXi Performance\|90th Percentile VM Disk Latency` | The 20-second peak virtual disk latency (ms) that 90 % of the powered-on VMs on the host are at or below. |
| Metric | `vCommunity\|ESXi Performance\|ESXi Bad Network Packets` | Errored and dropped packets as a % of all packets of the host in the last 5 minutes. Needs Total Packets Received and Transmitted activated in the [policy](../configuration-guide/policy.md). |
| Property | `vCommunity\|Configuration\|Advanced System Settings\|<setting>` | The value of an ESXi advanced system setting, such as `Disk.DiskRetryPeriod`. One property per setting listed in the ESXi advanced settings configuration file. |
| Property | `vCommunity\|Storage Adapter:<hba>\|Device` | Device name of the host bus adapter (HBA), such as `vmhba0`. One instance per HBA. |
| Property | `vCommunity\|Storage Adapter:<hba>\|Bus` | PCI bus number of the HBA. |
| Property | `vCommunity\|Storage Adapter:<hba>\|Model` | Model of the HBA, such as `NVMe SSD Controller`. |
| Property | `vCommunity\|Storage Adapter:<hba>\|PCI` | PCI address of the HBA, as bus:device.function. |
| Property | `vCommunity\|Storage Adapter:<hba>\|Status` | Status of the HBA, such as `online`, `offline` or `unknown`. |
| Property | `vCommunity\|Storage Adapter:<hba>\|Type` | Storage protocol of the HBA, such as `scsi`, `nvme`, `fc` or `iscsi`. |
| Property | `vCommunity\|Storage Adapter\|Number of HBA` | The number of HBAs on the host. |
| Property | `vCommunity\|Configuration\|VAAI\|ATS Heartbeat` | The `VMFS3.UseATSForHBOnVMFS5` setting: whether VMFS heartbeats use VAAI ATS (Atomic Test and Set). |
| Property | `vCommunity\|Configuration\|VAAI\|ATS Locking` | The `VMFS3.HardwareAcceleratedLocking` setting: whether VAAI hardware-accelerated locking is used. |
| Property | `vCommunity\|Configuration\|Config Status` | vCenter's configuration status of the host: green, yellow, red or gray. |
| Property | `vCommunity\|Configuration\|Max EVC` | The highest EVC mode the host's CPU supports. |
| Property | `vCommunity\|Network\|DHCP` | Whether the host's DNS settings come from DHCP (`config.network.dnsConfig.dhcp`): `True` or `False`. |
| Property | `vCommunity\|Network\|Search Domain` | The host's DNS search domains, comma-separated. |
| Property | `vCommunity\|Configuration\|Time Zone\|Name` | The short name of the host's time zone, such as `UTC`. |
| Property | `vCommunity\|Configuration\|Time Zone\|Description` | The description of the host's time zone. |
| Property | `vCommunity\|Configuration\|Time Zone\|GMT Offset` | The host's offset from GMT, in seconds. |
| Property | `vCommunity\|Runtime\|Boot Time` | When ESXi last booted. |
| Property | `vCommunity\|Hardware\|BIOS Vendor` | The vendor of the host's BIOS or firmware. |
| Property | `vCommunity\|Capability\|Storage vMotion Supported` | Whether the host supports Storage vMotion: `True` or `False`. |
| Property | `vCommunity\|Configuration\|Install Date\|UTC` | When ESXi was installed, in UTC (ISO 8601). Read from each host with a call to `imageConfigManager`. |
| Property | `vCommunity\|Licensing:<license>\|Name` | The name of the license assigned to the host, such as `Evaluation Mode`. |
| Property | `vCommunity\|Licensing:<license>\|License Key` | The license key. vCenter can return it partly masked. |
| Property | `vCommunity\|Licensing:<license>\|Edition Key` | The edition of the license, such as `esxEval` or `esxEnterprisePlus`. |
| Property | `vCommunity\|Licensing:<license>\|License Expiration Date` | When the license expires. Published only when the license has an expiration date, such as an evaluation license. |
| Metric | `vCommunity\|Licensing:<license>\|Remaining Days` | Days until the license expires. Published only when the license has an expiration date. |
| Property | `vCommunity\|Configuration\|Packages:<package>\|Package Name` | The name of a VIB listed in the ESXi packages configuration file. |
| Property | `vCommunity\|Configuration\|Packages:<package>\|Package Version` | The version of the VIB, with its build. |
| Property | `vCommunity\|Configuration\|Packages:<package>\|Acceptance Level` | The acceptance level of the VIB, such as `vmware_certified`, `partner` or `community`. |
| Property | `vCommunity\|Configuration\|Packages:<package>\|Maintenance Mode Required` | Whether installing or removing the VIB needs maintenance mode. |
| Property | `vCommunity\|Configuration\|Packages:<package>\|Package Summary` | The summary of the VIB. |
| Property | `vCommunity\|Configuration\|Packages:<package>\|Package Type` | The type of the package, such as `bootbank` or `tools`. |
| Property | `vCommunity\|Configuration\|Packages:<package>\|Package Vendor` | The vendor of the VIB, such as `VMware`, `VMW` or `Broadcom`. |
| Property | `vCommunity\|Network\|Device:<vmnic>\|Device Name` | The device name of the physical NIC, such as `vmnic0`. |
| Property | `vCommunity\|Network\|Device:<vmnic>\|Driver Version` | The driver version of the NIC. |
| Property | `vCommunity\|Network\|Device:<vmnic>\|Firmware Version` | The firmware version of the NIC. |
| Property | `vCommunity\|Network\|Device:<vmnic>\|Status` | `Connected` when the NIC reports a link speed, otherwise `Disconnected`. |
| Property | `vCommunity\|Network\|Device:<vmnic>\|PCI Vendor Name` | The vendor of the NIC's PCI device, such as `Broadcom`. |
| Property | `vCommunity\|Network\|Device:<vmnic>\|PCI Device Name` | The model of the NIC's PCI device. |
| Property | `vCommunity\|Network\|Device:<vmnic>\|PCI Vendor ID (VID)` | The PCI vendor ID, in hex, such as `15ad`. |
| Property | `vCommunity\|Network\|Device:<vmnic>\|PCI Device ID (DID)` | The PCI device ID, in hex. |
| Property | `vCommunity\|Network\|Device:<vmnic>\|PCI SubVendor ID (SVID)` | The PCI sub-vendor ID, in hex. |
| Property | `vCommunity\|Network\|Device:<vmnic>\|MAC` | The MAC address of the NIC. |
| Property | `vCommunity\|Network\|Device:<vmnic>\|Wake On Lan Supported` | Whether the NIC supports Wake-on-LAN. |
| Property | `vCommunity\|Network\|Device:<vmnic>\|PCI` | The PCI address of the NIC, as bus:device.function. |
| Property | `vCommunity\|Network\|Device:<vmnic>\|Duplex` | `full-duplex` when the link reports full duplex, otherwise `half-duplex`. A NIC with no link shows `half-duplex`. |

---

## Datastore

| Type | Key | Description |
| :--- | :--- | :--- |
| Property | `vCommunity\|Identifiers\|Number of Extents` | The number of VMFS extents of the datastore. 0 for a datastore that is not VMFS, or has no extents. |
| Property | `vCommunity\|Identifiers\|Extent:<index>\|ID` | The disk identifier (`naa.*`) of each extent. |
| Property | `vCommunity\|Summary\|MOID` | The managed object ID of the datastore in vCenter, such as `datastore-15`. |
| Property | `vCommunity\|Summary\|Block Size` | The VMFS block size, in MB. VMFS datastores only. |
| Property | `vCommunity\|Summary\|Max Blocks` | The maximum number of blocks. VMFS datastores only. |
| Property | `vCommunity\|Summary\|VMFS Upgradable` | Whether the VMFS version can be upgraded. VMFS datastores only. |
| Property | `vCommunity\|Summary\|Status` | vCenter's status of the datastore: green, yellow, red or gray. |
| Property | `vCommunity\|Summary\|SIOC Enabled` | Whether Storage I/O Control is enabled. |
| Property | `vCommunity\|Summary\|SIOC Threshold` | The latency, in ms, at which Storage I/O Control starts to act. |

---

## Virtual Machine

| Type | Key | Description |
| :--- | :--- | :--- |
| Metric | `vCommunity\|VM Performance\|VM Performance Score` | KPI, 0 to 100 %, of a powered-on VM, from 9 sub-metrics. 100 is best. See [VM Performance](metrics/vm-performance.md). |
| Metric | `vCommunity\|VM Performance\|Memory Zip Swap` | Compressed plus swapped memory of the VM, as a % of the memory the guest uses. |
| Metric | `vCommunity\|Configuration\|Share per vCPU` | CPU shares ÷ vCPUs, on every VM. Normal is 1000. Published as a metric until [issue #49](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/49) is fixed. See [VM Shares](metrics/vm-shares.md#known-limitations). |
| Metric | `vCommunity\|Configuration\|Share per MB of Memory` | Memory shares ÷ configured MB, on every VM. Normal is 10. Published as a metric until [issue #49](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/49) is fixed. See [VM Shares](metrics/vm-shares.md#known-limitations). |
| Metric | `vCommunity\|VM Guest OS KPI` | The average (0 to 100 %) of VM Performance Score and Guest OS Performance Score. A VM without Guest OS Performance gets its VM Performance Score. A VM without VM Performance Score gets no value. |
| Metric | `vCommunity\|Guest OS Performance\|Guest OS Performance Score` | KPI, 0 to 100 %, of the guest OS of a powered-on VM with VMware Tools, from 4 sub-metrics. 100 is best. See [Guest OS Performance](metrics/guest-os-performance.md). |
| Property | `vCommunity\|Options\|<config path>` | The value of a VM configuration field, such as `config.bootOptions.bootDelay`. One property per path listed in the VM Options configuration file. Not published when the value is empty. |
| Property | `vCommunity\|Configuration\|Advanced Parameters\|<key>` | The value of a VM advanced parameter (`extraConfig`), such as `svga.present`. One property per key listed in the VM advanced parameters configuration file. |
| Metric | `vCommunity\|Configuration\|SCSI Controllers\|Count` | The number of SCSI controllers of the VM. |
| Property | `vCommunity\|Configuration\|SCSI Controllers:<bus>\|Type` | The type of a SCSI controller, such as VMware Paravirtual (PVSCSI), LSI Logic SAS, LSI Logic Parallel or BusLogic. |
| Property | `vCommunity\|Network\|Network Adapters:<adapter>\|Type` | How the MAC address of the network adapter is assigned: `assigned`, `generated` or `manual`. |
| Property | `vCommunity\|Network\|Network Adapters:<adapter>\|Starts Connected` | Whether the network adapter connects when the VM powers on. |
| Property | `vCommunity\|Virtual Disk:<disk>\|Label` | The label of the virtual disk, such as `Hard disk 1`. |
| Property | `vCommunity\|Virtual Disk:<disk>\|Key` | The device key of the virtual disk. |
| Property | `vCommunity\|Virtual Disk:<disk>\|Controller Key` | The device key of the controller the disk is on. |
| Property | `vCommunity\|Virtual Disk:<disk>\|Eagerly Scrub` | Whether the disk is eager-zeroed thick. |
| Property | `vCommunity\|Virtual Disk:<disk>\|Split` | Whether the disk file is split into 2 GB pieces. |
| Property | `vCommunity\|Virtual Disk:<disk>\|Write Through` | Whether the disk is in write-through mode. |
| Property | `vCommunity\|Virtual Disk:<disk>\|Storage Allocation Share Level` | The storage I/O share level of the disk: low, normal, high or custom. |
| Property | `vCommunity\|Configuration\|NUMA\|Hot Add Exposed` | Whether vNUMA is exposed to the guest while CPU hot-add is enabled. |
| Property | `vCommunity\|Configuration\|CPU Allocation Share Level` | The CPU share level of the VM: low, normal, high or custom. |
| Property | `vCommunity\|Configuration\|Boot Options\|Delay` | The delay, in ms, before the VM boots. |
| Property | `vCommunity\|Configuration\|Boot Options\|Retry Delay` | The wait, in ms, before the VM retries a failed boot. |
| Property | `vCommunity\|Configuration\|Boot Options\|Retry Enabled` | Whether the VM retries a failed boot. |
| Property | `vCommunity\|Configuration\|Boot Options\|Enter BIOS Setup` | Whether the VM enters BIOS or UEFI setup at the next power-on. |
| Property | `vCommunity\|Configuration\|Change Version` | The change version of the VM configuration, which changes at each configuration update. |
| Property | `vCommunity\|Configuration\|Firmware` | The firmware of the VM: `bios` or `efi`. |
| Property | `vCommunity\|Configuration\|Flags\|Disk UUID Enabled` | Whether disk UUIDs are exposed to the guest. |
| Property | `vCommunity\|Configuration\|Latency Sensitivity Level` | The latency sensitivity of the VM: low, normal, medium or high. Higher levels reserve CPU and network resources for the VM. |
| Property | `vCommunity\|Configuration\|Reboot PowerOff` | Whether a reboot from the guest powers the VM off instead. |
| Property | `vCommunity\|Configuration\|Hardware Upgrade\|Status` | The status of a scheduled hardware version upgrade, such as `none`, `pending` or `error`. |
| Property | `vCommunity\|Configuration\|Hardware Upgrade\|Policy` | When the hardware version is upgraded: `never`, `onSoftPowerOff` or `always`. |
| Property | `vCommunity\|Configuration\|Hardware Upgrade\|Target Version` | The target hardware version of a scheduled upgrade. |
| Property | `vCommunity\|Configuration\|Op Notification Timeout` | The timeout, in seconds, of guest operation notifications. A negative value is shown as 0. |
| Property | `vCommunity\|Configuration\|Memory Allocation Share Level` | The memory share level of the VM: low, normal, high or custom. |
| Property | `vCommunity\|Configuration\|Config Status` | vCenter's configuration status of the VM: green, yellow, red or gray. |
| Property | `vCommunity\|Guest\|State` | The state of the guest OS, such as `running`, `notRunning` or `shuttingDown`. |
| Property | `vCommunity\|Guest\|Application Status` | The application heartbeat status of the guest. |
| Property | `vCommunity\|Guest\|Kernel Crash State` | Whether the guest kernel has crashed. |
| Property | `vCommunity\|Guest\|Operation Ready` | Whether guest operations, such as file and process management, are available. |
| Property | `vCommunity\|Guest\|State Change Support` | Whether the guest supports state changes such as standby. |
| Property | `vCommunity\|Guest\|Interactive Guest` | Whether VMware Tools runs in an interactive user session. |
| Property | `vCommunity\|Guest\|Tools Sync Time` | Whether VMware Tools synchronizes the guest clock with the host. |
| Property | `vCommunity\|Guest\|Tools Upgrade Policy` | The VMware Tools upgrade policy, such as `manual` or `upgradeAtPowerCycle`. |
| Property | `vCommunity\|Runtime\|Consolidation Needed` | Whether the VM's disks need consolidation after a snapshot operation. |
| Property | `vCommunity\|Runtime\|DAS protection` | Whether vSphere HA protects the VM. |
| Property | `vCommunity\|Runtime\|Min Required EVC Mode Key` | The lowest EVC mode the VM can run on, from the CPU features it uses. |
| Property | `vCommunity\|Guest\|Customization Status` | The status of guest customization, without the `TOOLSDEPLOYPKG_` prefix. |
| Property | `vCommunity\|Guest\|Heartbeat Status` | The VMware Tools heartbeat status: green, yellow, red or gray. |
| Property | `vCommunity\|Guest\|Detailed Data\|Build Number` | The build number of the guest OS, from the VMware Tools `guestDetailedData`. |
| Property | `vCommunity\|Guest\|Detailed Data\|CPE String` | The Common Platform Enumeration (CPE) name of the guest OS. |
| Property | `vCommunity\|Guest\|Detailed Data\|Distro Additional Version` | Additional version information of the guest OS distribution. |
| Property | `vCommunity\|Guest\|Detailed Data\|Distro Name` | The name of the guest OS distribution, such as `Ubuntu` or `VMware Photon OS`. |
| Property | `vCommunity\|Guest\|Detailed Data\|Distro Version` | The version of the guest OS distribution. |
| Property | `vCommunity\|Guest\|Detailed Data\|Kernel Version` | The kernel version of the guest OS. |
| Property | `vCommunity\|Guest\|Detailed Data\|Pretty Name` | The full name of the guest OS, such as `Ubuntu 24.04.4 LTS`. |
| Property | `vCommunity\|Summary\|VM Path Name` | The datastore path of the VM's `.vmx` file. |

### Windows guests

These properties are read inside Windows VMs through the vSphere Guest API. They need **Guest OS Service Monitoring Status** set to `Enabled` on the Adapter Instance, the Windows user name and password in its credential, and VMware Tools running in the VM. See [Adapter Instance](../configuration-guide/adapter-instance.md#2-advanced-settings-optional) and [What runs inside a Windows VM](../configuration-guide/tls-and-security.md#what-runs-inside-a-windows-vm).

| Type | Key | Description |
| :--- | :--- | :--- |
| Property | `vCommunity\|Guest OS\|Services:<display name>\|Service Name` | The name of a Windows service listed in the Windows service configuration file. |
| Property | `vCommunity\|Guest OS\|Services:<display name>\|Service Status` | The status of the service, such as `Running` or `Stopped`. |
| Property | `vCommunity\|Guest OS\|Services:<display name>\|Service Start Type` | The start type of the service, such as `Automatic` or `Manual`. |
| Property | `vCommunity\|Guest OS\|Operating System\|OS Name` | The name of the Windows edition. |
| Property | `vCommunity\|Guest OS\|Operating System\|OS Version` | The Windows version. |
| Property | `vCommunity\|Guest OS\|Operating System\|OS BuildNumber` | The Windows build number. |
| Property | `vCommunity\|Guest OS\|Operating System\|OS Architecture` | The architecture, such as `64-bit`. |
| Property | `vCommunity\|Guest OS\|Operating System\|OS Last Boot Up Time` | When Windows last started. |
| Property | `vCommunity\|Guest OS\|Operating System\|OS Release ID` | The Windows release ID, read from the registry. |

---

## vCenter

| Type | Key | Description |
| :--- | :--- | :--- |
| Metric | `vCommunity\|Availability\|Worst Cluster Operational Availability` | The lowest Cluster Operational Availability of the clusters of this vCenter, from the same collection cycle. See [Operational Availability](metrics/operational-availability.md#known-limitations). |
| Property | `vCommunity\|Certificate\|SHA-256 Thumbprint` | The SHA-256 thumbprint of the certificate the vCenter presents now. See [Trust on First Use](../configuration-guide/tls-and-security.md#trust-on-first-use). |
| Property | `vCommunity\|Certificate\|Status` | `Recorded`, `Unchanged`, `Changed` (a different certificate within the last 24 hours) or `Unknown` (the certificate could not be read). |
| Property | `vCommunity\|Certificate\|Previous SHA-256 Thumbprint` | The thumbprint before the last change. |
| Property | `vCommunity\|Certificate\|Last Changed` | When the last certificate change was seen, in UTC. |
| Property | `vCommunity\|Configuration\|Patch Level` | The patch level of vCenter Server. |
| Property | `vCommunity\|Configuration\|User Directory Timeout` | The timeout, in seconds, of user directory (AD or LDAP) queries. |
| Property | `vCommunity\|Configuration\|Enable MOB` | Whether the Managed Object Browser (MOB) is enabled. |
| Property | `vCommunity\|Configuration\|Database\|Event retention (days)` | How many days vCenter keeps events. |
| Property | `vCommunity\|Configuration\|Database\|Event Cleanup Enabled` | Whether vCenter deletes old events. |
| Property | `vCommunity\|Configuration\|Database\|Task retention (days)` | How many days vCenter keeps tasks. |
| Property | `vCommunity\|Configuration\|Database\|Task Cleanup Enabled` | Whether vCenter deletes old tasks. |
| Property | `vCommunity\|Configuration\|Runtime\|vCenter Unique ID` | The unique instance ID of vCenter Server. |
| Property | `vCommunity\|Configuration\|Runtime\|vCenter managed address` | The managed IP address of vCenter Server. |
| Property | `vCommunity\|Configuration\|Database\|Maximum Connections` | The maximum number of database connections. |
| Property | `vCommunity\|Configuration\|Log Level` | The log level of vCenter Server, such as `info`, `warning` or `debug`. |
| Metric | `vCommunity\|Number of Port Groups` | The port groups of this vCenter, distributed and standard, counted per Datacenter. When a read fails, nothing is published, so the last value stays. See [Port groups and VMware Tools](metrics/vsphere-world-metrics.md#port-groups-and-vmware-tools). |
| Metric | `vCommunity\|Collection Health\|Warnings in Last Cycle` | The number of warnings and errors in the adapter log during the last collection cycle. The Collection Warnings alert uses it. See [Symptoms](../troubleshooting-guide/symptoms.md#a-collection-warnings-alert-is-shown). |
| Property | `vCommunity\|Collection Health\|First Warning` | The first warning or error of the last collection cycle, cut to 250 characters, or `None in the last cycle`. Read it first when the alert is active. |

---

## vSphere World

| Type | Key | Description |
| :--- | :--- | :--- |
| Metric | `vCommunity\|Worst 10 Percent Cluster Performance` | The Cluster Performance score that 90 % of all clusters, of all vCenters, are at or above. Can be one collection cycle old. See [vSphere World Cluster Metrics](metrics/vsphere-world-metrics.md#known-limitations). |
| Metric | `vCommunity\|Worst Cluster Performance` | The lowest Cluster Performance score of all clusters. |
| Metric | `vCommunity\|Worst 10 Percent Cluster Risk` | The Cluster Risk that 90 % of all clusters are at or below. Cluster Risk is higher-is-worse. |
| Metric | `vCommunity\|Worst Cluster Risk` | The highest Cluster Risk of all clusters. |
| Metric | `vCommunity\|Highest 10 Percent Cluster Utilization` | The Cluster Consumption score that 10 % of all clusters are at or above. Cluster Consumption is higher-is-worse. |
| Metric | `vCommunity\|Highest Cluster Utilization` | The highest Cluster Consumption score of all clusters. |
| Metric | `vCommunity\|Availability\|Worst Cluster Operational Availability` | The lowest Cluster Operational Availability of all clusters, of all vCenters. Can be one collection cycle old. See [Operational Availability](metrics/operational-availability.md#known-limitations). |
| Metric | `vCommunity\|Availability\|ESXi Hosts Operational Availability` | The average ESXi Host Operational Availability of the hosts with a value from the last 10 minutes, of all vCenters. |
| Metric | `vCommunity\|Network\|Total Network Speed Degradation` | The number of hosts below 100 % Network Speed Degradation, of all vCenters. Can be one collection cycle old. See [Network Speed Degradation](metrics/network-speed-degradation.md#known-limitations). |
| Metric | `vCommunity\|Cluster Delta Close Count` | The number of clusters whose Close for Business changed from 0 to 1 since the previous Periodic Cluster Check window. Published once per window. See [Close for Business changes](metrics/vsphere-world-metrics.md#close-for-business-changes). |
| Metric | `vCommunity\|Cluster Delta Open Count` | The number of clusters whose Close for Business changed from 1 to 0 since the previous window. Published once per window. |
| Metric | `vCommunity\|Number of Port Groups` | The sum of the vCenters' port group counts, using each vCenter's value for up to 15 minutes. Published as 0 when no vCenter has a value that recent. See [Port groups and VMware Tools](metrics/vsphere-world-metrics.md#port-groups-and-vmware-tools). |
| Metric | `vCommunity\|Number of VM without Tools` | VMs whose VMware Tools are not installed, whatever their power state. |
| Metric | `vCommunity\|Number of VMware Tools down` | Powered-on VMs whose VMware Tools are installed but not running. |

---

## Datacenter

| Type | Key | Description |
| :--- | :--- | :--- |
| Metric | `vCommunity\|Network\|Total Network Speed Degradation` | The number of hosts of the Datacenter below 100 % Network Speed Degradation, from the same collection cycle. See [Network Speed Degradation](metrics/network-speed-degradation.md#known-limitations). |

---

## Content Library

A content library of the vCenter, local or subscribed. The pack creates this object type. It is read from the vSphere Automation REST API in every collection cycle, with one call per library item. The pack does not link the library to the vCenter object. See [Templates and Content Libraries](../concepts/templates-and-content-libraries.md).

| Type | Key | Description |
| :--- | :--- | :--- |
| Property | `vCommunity\|Content Library\|Type` | The library type as vCenter reports it: `LOCAL` or `SUBSCRIBED`. |
| Property | `vCommunity\|Content Library\|Subscription URL` | The published library this library subscribes to. Empty for a local library. |
| Property | `vCommunity\|Content Library\|Automatic Sync` | Whether the library syncs automatically. |
| Property | `vCommunity\|Content Library\|State` | The state of the library in vCenter. |
| Metric | `vCommunity\|Content Library\|Items` | The number of items. |
| Metric | `vCommunity\|Content Library\|Items Not Stored Locally` | Items whose `cached` field is false or missing. |
| Metric | `vCommunity\|Content Library\|Items Not Security Compliant` | Items whose `security_compliance` field is false or missing. |
| Metric | `vCommunity\|Content Library\|Total Size (GB)` | The total size of the items. |

---

## Library Item

One item of a content library, of any type: OVF, OVA, VM template, ISO and others. The pack creates this object type. Its parent is its Content Library.

| Type | Key | Description |
| :--- | :--- | :--- |
| Property | `vCommunity\|Library Item\|Type` | The item type. |
| Property | `vCommunity\|Library Item\|Description` | The description of the item. |
| Property | `vCommunity\|Library Item\|Version` | The version of the item. |
| Property | `vCommunity\|Library Item\|Content Version` | The content version of the item. |
| Property | `vCommunity\|Library Item\|Stored Locally` | Whether the item's files are stored in the library (`cached`). |
| Property | `vCommunity\|Library Item\|Security Compliant` | The `security_compliance` value. |
| Property | `vCommunity\|Library Item\|Certificate Verification` | The certificate verification status. |
| Property | `vCommunity\|Library Item\|Last Modified` | When the item was last modified. |
| Property | `vCommunity\|Library Item\|Last Sync` | When the item was last synchronized. |
| Property | `vCommunity\|Library Item\|Source Item ID` | The ID of the published item this item comes from, in a subscribed library. |
| Metric | `vCommunity\|Library Item\|Size (GB)` | The size of the item. |

---

## VM Template

A virtual machine marked as a template in vCenter. The pack creates this object type. It has no parent link and no children: the pack does not link it to its folder, and the VMs cloned from it are not linked, because neither vCenter nor VCF Operations stores which template a VM came from. See [Template and Content Library Design](../development-guide/template-and-library-design.md).

| Type | Key | Description |
| :--- | :--- | :--- |
| Property | `vCommunity\|VM Template\|Guest OS` | The guest operating system. |
| Property | `vCommunity\|VM Template\|Hardware Version` | The virtual hardware version. |
| Property | `vCommunity\|VM Template\|vCPUs` | The number of virtual CPUs. |
| Property | `vCommunity\|VM Template\|Memory (GB)` | The memory, in GB. |
| Property | `vCommunity\|VM Template\|Datastore` | The datastores that hold the template's disks. |
| Property | `vCommunity\|VM Template\|VM Folder` | The folder the template is in. |
| Metric | `vCommunity\|VM Template\|Disk Used (GB)` | The disk space the template uses. |

---

## Business Application objects

These metrics are published on Container objects of the kinds Tier, Business Application (BusinessService) and Enterprise. The pack does not own these objects. The values are calculated from the VMs and Kubernetes namespaces of each object. See [Business Application Performance](metrics/business-application-performance.md).

| Type | Key | Description |
| :--- | :--- | :--- |
| Metric | `vCommunity\|Business Application\|Tier Performance` | On a Tier: the average VM Guest OS KPI of its VMs (0 to 100 %). Not published when no VM has a value. |
| Metric | `vCommunity\|Business Application\|Business Application Performance` | On a Business Application: the highest of its K8S Namespace performance values and its lowest Tier Performance (0 to 100 %). Not published when neither has a value. |
| Metric | `vCommunity\|Business Application\|Business Applications Performance` | On an Enterprise: the average of its Business Applications (0 to 100 %). Not published when none has a value. |

---

## Events

The pack also sends events. They appear in the events of the object in VCF Operations, and cancel themselves.

| Object | Event | When |
| :--- | :--- | :--- |
| vCenter | `vCommunity configuration: <problem>`, warning | A configuration file named by the Adapter Instance is missing, cannot be read or is not valid XML. It cancels a few cycles after the file is fixed. See [Configuration Files](../troubleshooting-guide/configuration-files.md). |
| Virtual Machine | `[WindowsEvent-<level> <message>]` | A Windows event whose log and Event ID are listed in the Windows event configuration file. Needs **Windows Event Log Monitoring Status** set to `Enabled`, and the same Windows credential and VMware Tools as the Windows properties above. The criticality follows the Windows level: Information and Verbose are info, Warning is warning, Error is immediate, Critical is critical. At most 100 events per VM per cycle. |

---

## Super metrics replaced by built-in metrics

These super metrics were removed from `content/supermetrics`. The pack's dashboards, reports and views now use the built-in metric. If you built your own content on them, change it the same way.

| Removed super metric | Object | Replaced by |
| :--- | :--- | :--- |
| vSphere Cluster Performance | Cluster | `vCommunity\|Cluster Performance\|Cluster Performance Score` |
| vSphere Cluster Worst VM CPU Ready | Cluster | `vCommunity\|Cluster Performance\|Worst VM CPU Ready` |
| vSphere Cluster Worst VM CPU Co-Stop | Cluster | `vCommunity\|Cluster Performance\|Worst VM CPU Co-Stop` |
| vSphere Cluster Worst VM Memory Contention | Cluster | `vCommunity\|Cluster Performance\|Worst VM Memory Latency` |
| vSphere Cluster Worst ESXi Bad Network Packets | Cluster | `vCommunity\|Cluster Performance\|Highest ESXi Bad Network Packets` |
| vSphere Cluster CPU Ready (average of the VMs) | Cluster | `vCommunity\|Cluster Performance\|90th Percentile VM CPU Ready` |
| vSphere Cluster CPU Co-Stop (average of the VMs) | Cluster | `vCommunity\|Cluster Performance\|90th Percentile VM CPU Co-Stop` |
| vSphere Cluster Memory Contention (average of the VMs) | Cluster | `vCommunity\|Cluster Performance\|90th Percentile VM Memory Latency` |
| vSphere Cluster Memory Zip Swap (cluster total) | Cluster | `vCommunity\|Cluster Risk\|Worst ESXi Memory Zip Swap` |
| vSphere Cluster Memory Ballooned (cluster total) | Cluster | `vCommunity\|Cluster Risk\|Worst ESXi Memory Ballooned` |
| CPU Reservation (cluster total) | Cluster | `vCommunity\|Cluster Risk\|Highest ESXi CPU Reservation` |
| Memory Reservation (cluster total) | Cluster | `vCommunity\|Cluster Risk\|Highest ESXi Memory Reservation` |
| Cluster Operational Availability | Cluster | `vCommunity\|Availability\|Cluster Operational Availability` |
| Number of Resource Pools | Cluster | `vCommunity\|Resource Pools\|Number of Resource Pools` |
| Cascading Resource Pools | Cluster | `vCommunity\|Resource Pools\|Cascading Resource Pools` |
| ESXi Bad Network Packets | Host | `vCommunity\|ESXi Performance\|ESXi Bad Network Packets` |
| ESXi Host Operational Availability ("ESXi Host Availability") | Host | `vCommunity\|Availability\|ESXi Host Operational Availability` |
| Network Speed Degradation | Host | `vCommunity\|Network\|Network Speed Degradation` |
| vSphere VM Memory Zip Swap | VM | `vCommunity\|VM Performance\|Memory Zip Swap` |
| vSphere VM Performance | VM | `vCommunity\|VM Guest OS KPI` |
| Share per vCPU | VM | `vCommunity\|Configuration\|Share per vCPU` (a metric until issue #49 is fixed) |
| Share per GB of Memory | VM | `vCommunity\|Configuration\|Share per MB of Memory` (a metric until issue #49 is fixed). The values are the same: the super metric was per MB despite its name. |
| Number of Port Groups | Distributed Switch | `vCommunity\|Number of Port Groups` on vSphere World and on each vCenter. It is not a per-switch value, so the per-switch columns in the Distributed Switch and Set views were removed. |
| vSphere Clusters Performance (average of all clusters) | vSphere World | `vCommunity\|Worst 10 Percent Cluster Performance` |
| ESXi Hosts Operational Availability ("ESXi Hosts Average Availability") | vSphere World | `vCommunity\|Availability\|ESXi Hosts Operational Availability` |
| Total Network Speed Degradation | vSphere World, Datacenter | `vCommunity\|Network\|Total Network Speed Degradation` |
| Worst Cluster Operational Availability | vSphere World, vCenter | `vCommunity\|Availability\|Worst Cluster Operational Availability`. No longer provided on Custom Datacenter. |
| vSphere Clusters not Green | vSphere World | Removed. No built-in metric replaces it. |
| Business Application Tier Performance | Tier | `vCommunity\|Business Application\|Tier Performance` |
| Business Application Performance | Business Application | `vCommunity\|Business Application\|Business Application Performance` |
| Business Applications Performance | Enterprise | `vCommunity\|Business Application\|Business Applications Performance` |

Why the replacements differ from the super metrics:

- Averages became percentiles, which a super metric cannot calculate: the 90th percentile of the VM values, and the 10th percentile of the cluster scores.
- Cluster totals became the worst or highest ESXi host, because one full host hurts its VMs even when the cluster total looks fine.

### Renamed keys

Version 0.8.0 renamed three vSphere World metrics. The old keys are no longer updated. Change any content that still uses them.

| Old key | New key |
| :--- | :--- |
| `vCommunity\|Bottom 10 Percent Cluster Performance` | `vCommunity\|Worst 10 Percent Cluster Performance` |
| `vCommunity\|Bottom 10 Percent Cluster Risk` | `vCommunity\|Worst 10 Percent Cluster Risk` |
| `vCommunity\|Top 10 Percent Cluster Utilization` | `vCommunity\|Highest 10 Percent Cluster Utilization` |
