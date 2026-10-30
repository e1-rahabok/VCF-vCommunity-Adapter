#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

# The adapter definition: the object types, groups, metrics, properties and parameters VCF Operations shows.
# adapter.py calls get_adapter_definition(). Adding a KPI or metric to a module's table is done in that module.

import constants.main
import aria.ops.adapter_logging as logging
from aria.ops.definition.adapter_definition import AdapterDefinition
from aria.ops.definition.units import Units
from aria.ops.timer import Timer
from metrics.cluster import (
    cluster_performance_metrics, cluster_risk_metrics, cluster_consumption_metrics, cluster_availability,
    periodic_cluster_check, resource_pool_counts,
)
from metrics.host import esxi_performance_metrics, host_availability, host_network_speed
from metrics.vm import vm_performance_metrics, guest_os_performance_metrics, vm_guest_os_kpi
from properties.vm import vm_shares
from metrics.world import cluster_summary_metrics, availability_summary_metrics, cluster_close_changes
from metrics.world import port_group_counts, vm_tools_counts
from metrics.vcenter import vcenter_port_groups, vcenter_availability
from metrics.container import business_app_performance
from metrics.datacenter import datacenter_network_degradation
from utils import collection_health
from utils import guest_http
from utils import tls
from collectors.library.collectLibraryData import ITEM_ID_KEY, ITEM_KIND, LIBRARY_ID_KEY, LIBRARY_KIND
from collectors.library.collectTemplateData import TEMPLATE_KIND

logger = logging.getLogger(__name__)


# The units used in the KPI tables, as the SDK unit each one stands for. The SDK does not accept plain text.
KPI_UNITS = {
    None: None,
    "%": Units.RATIO.PERCENT,
    "ms": Units.TIME.MILLISECONDS,
    "µs": Units.TIME.MICROSECONDS,
    "MB": Units.DATA_SIZE.MEGABYTE,
}


def define_kpi(vCommunity, kpi) -> None:
    # kpi is a KPI module, such as cluster_performance_metrics. Its metric list lives in one place: that module.
    group = vCommunity.define_group(kpi.GROUP, kpi.GROUP)
    for metric in kpi.PUBLISHED_METRICS:
        group.define_metric(metric.name, metric.name, unit=KPI_UNITS[metric.unit])
    group.define_metric(kpi.KPI_KEY, kpi.KPI_NAME, unit=Units.RATIO.PERCENT)


def define_availability(vCommunity, *metric_names: str) -> None:
    # Operational Availability metrics, in the "Availability" group, on the object types that publish them.
    group = vCommunity.define_group(host_availability.GROUP, host_availability.GROUP)
    for name in metric_names:
        group.define_metric(name, name, unit=Units.RATIO.PERCENT)


def define_network_count(vCommunity) -> None:
    # Total Network Speed Degradation, in the "Network" group, on the Datacenter and vSphere World.
    group = vCommunity.define_group(host_network_speed.GROUP, host_network_speed.GROUP)
    group.define_metric(datacenter_network_degradation.COUNT_METRIC, datacenter_network_degradation.COUNT_METRIC)


def get_adapter_definition() -> AdapterDefinition:
    with Timer(logger, "Get Adapter Definition"):
        definition = AdapterDefinition(constants.main.ADAPTER_KIND, constants.main.ADAPTER_NAME)

        definition.define_string_parameter(
            constants.main.HOST_IDENTIFIER,
            "vCenter Server",
            description="The FQDN or IP address of the vCenter Server to collect from. Example: "
                        "vcenter01.corp.local. Use the same name as the vCenter's own adapter instance in VCF "
                        "Operations, so the properties land on the right objects.",
        )

        definition.define_string_parameter(
            "esxi_adv_settings_config_file",
            label="ESXi Advanced System Settings Config File",
            description="The name of the configuration file that lists the ESXi advanced settings to collect as "
                        "properties. Give the name without .xml. Example: esxi_advanced_system_settings_prod. "
                        "Find the files under Configurations > Management Pack Configuration. The default file "
                        "is a reference with every entry commented out, so it collects nothing. Clone it, "
                        "uncomment the settings you want, and enter the clone's name here. A property stays on "
                        "the object once it has been collected, so add only the settings you need.",
            default="esxi_advanced_system_settings",
            required=False,
        )

        definition.define_string_parameter(
            "esxi_vib_driver_config_file",
            label="ESXi Software Packages Config File",
            description="The name of the configuration file that lists the ESXi software packages (VIBs and "
                        "drivers) whose versions are collected as properties. Give the name without .xml. "
                        "Example: esxi_packages_prod. The default file is a reference with every entry commented "
                        "out. Clone it, uncomment the packages you want, such as nmlx5_core or lpfc, and enter "
                        "the clone's name here.",
            default="esxi_packages",
            required=False,
        )

        definition.define_string_parameter(
            "vm_adv_settings_config_file",
            label="VM Advanced Parameters Config File",
            description="The name of the configuration file that lists the VM advanced parameters (.vmx "
                        "settings) to collect as properties. Give the name without .xml. Example: "
                        "vm_advanced_parameters_prod. Clone the default reference file, keep only the parameters "
                        "you need, and enter the clone's name here. Each parameter is collected for every VM, so "
                        "a long list adds to the collection time.",
            default="vm_advanced_parameters",
            required=False,
        )

        definition.define_string_parameter(
            "vm_configuration_config_file",
            label="VM Options Config File",
            description="The name of the configuration file that lists the VM Options settings to collect as "
                        "properties. Give the name without .xml. Example: vm_options_prod. Clone the default "
                        "reference file, keep only the options you need, and enter the clone's name here.",
            default="vm_options",
            required=False,
        )

        definition.define_int_parameter(
            constants.main.PORT_IDENTIFIER, "Port", default=443, advanced=True,
            description="The HTTPS port of the vCenter Server. Example: 443. Leave it at 443 unless your vCenter "
                        "is reached through a proxy or load balancer on another port.",
        )

        definition.define_enum_parameter(
            constants.main.VCENTER_TLS_VALIDATION,
            values=tls.VCENTER_MODES,
            label="vCenter TLS Validation",
            description="Trust on First Use (the default) connects whatever the certificate, records its "
                        "thumbprint on the vCenter object, and reports when it changes, without stopping. "
                        "WARNING: it sends the user name and password before the certificate is checked, so an "
                        "impostor on the first connection receives them. Use Pinned or Enabled on a network you do not "
                        "fully trust. "
                        "Enabled: the certificate must be trusted by the Cloud Proxy, or the adapter does not "
                        "connect. Pinned: the certificate must match the vCenter Thumbprint below, or the adapter "
                        "does not connect.",
            default=tls.DEFAULT_VCENTER_MODE,
            required=False,
            advanced=True,
        )

        definition.define_string_parameter(
            constants.main.VCENTER_THUMBPRINT,
            label="vCenter Thumbprint (SHA-256)",
            description="The SHA-256 thumbprint of the vCenter certificate, as AA:BB:CC:... Only used when "
                        "vCenter TLS Validation is Pinned.",
            required=False,
            advanced=True,
        )

        definition.define_enum_parameter(
            periodic_cluster_check.PERIOD_SETTING,
            values=periodic_cluster_check.PERIOD_CHOICES,
            label="Cluster Check Period (hours)",
            description="How often you run the check on the cluster's Close or Open for Business status. Start "
                        "with 6 hours, so you can check faster. Once you're comfortable, set it to 24 hours to "
                        "match your daily capacity reviews each morning. Use a shorter period if you need to "
                        "react within the day, but expect the result to be more volatile.",
            default=periodic_cluster_check.DEFAULT_PERIOD,
            required=False,
            advanced=True,
        )

        definition.define_string_parameter(
            periodic_cluster_check.TIME_SETTING,
            label="Cluster Check Time (UTC)",
            description="The time of day, as HH:MM in UTC, when a window ends. The other windows end every "
                        "period after that. Example: with 06:00 and a 6-hour period, windows end at 00:00, 06:00, "
                        "12:00 and 18:00 UTC. With 22:00 and 24 hours, each result covers 22:00 to 22:00 UTC. "
                        "Pick a time just after your busy day ends, so a day's results cover a whole business "
                        "day. Results appear within a few collection cycles after the window ends.",
            default=periodic_cluster_check.DEFAULT_TIME,
            required=False,
            advanced=True,
        )

        definition.define_int_parameter(
            periodic_cluster_check.WORST_PERCENT_SETTING,
            label="Cluster Check Worst Percent",
            description="How much of each window's worst time is ignored. Example: with a 24-hour window, "
                        "setting the bottom 5% means ignoring the worst 14 samples (about 70 minutes). Basically, "
                        "the 15th-worst value is reported. Setting the value to 0 means the single worst 5-minute "
                        "sample is returned. 0 to 50.",
            default=periodic_cluster_check.DEFAULT_WORST_PERCENT,
            required=False,
            advanced=True,
        )

        # The size at which a VM becomes a monster on its host, for Cluster Risk. See cluster_risk_metrics.py.
        definition.define_int_parameter(
            cluster_risk_metrics.MONSTER_CPU_SETTING,
            label="Monster VM CPU (% of host cores)",
            description="When a VM counts as a CPU monster on its host. A VM is one when its vCPUs exceed this "
                        "% of the host's physical cores. Hyperthreads don't count. Monster VMs raise Cluster "
                        "Risk, because they're hard to place and to vMotion. Example: at 50 (the default), on a "
                        "host with 64 cores and 128 threads, a VM with more than 32 vCPUs is a monster. Range 1 "
                        "to 100. Lower it if large VMs already give you placement or co-stop trouble at smaller "
                        "sizes.",
            default=cluster_risk_metrics.DEFAULT_MONSTER_CPU_PERCENT,
            required=False,
            advanced=True,
        )

        definition.define_int_parameter(
            cluster_risk_metrics.MONSTER_MEMORY_SETTING,
            label="Monster VM Memory (% of host DRAM)",
            description="When a VM counts as a memory monster on its host. A VM is one when its configured "
                        "memory exceeds this % of the host's DRAM, or exceeds Monster VM Memory Minimum, "
                        "whichever is smaller. Memory tiering (NVMe) doesn't count. Example: at 40 (the default), "
                        "on a host with 512 GB of DRAM, the limit is the smaller of 205 GB and 256 GB, so a VM "
                        "over 205 GB is a monster. Range 1 to 100.",
            default=cluster_risk_metrics.DEFAULT_MONSTER_MEMORY_PERCENT,
            required=False,
            advanced=True,
        )

        definition.define_int_parameter(
            cluster_risk_metrics.MONSTER_MEMORY_MIN_SETTING,
            label="Monster VM Memory Minimum (GB)",
            description="A memory size that makes a VM a memory monster on any host, however large the host is. "
                        "Example: at 256 (the default), on a host with 2 TB of DRAM (where 40% would be 819 GB), "
                        "a 300 GB VM is still a monster. On a smaller host the % of host DRAM gives the lower "
                        "limit, so a smaller VM already counts. Set it to the largest VM your team can "
                        "comfortably move or restart on any host.",
            default=cluster_risk_metrics.DEFAULT_MONSTER_MEMORY_MIN_GB,
            required=False,
            advanced=True,
        )

        definition.define_string_parameter(
            "win_service_config_file",
            label="Windows Service Configuration File",
            description="The name of the configuration file that lists the Windows services to check inside "
                        "guest VMs. Give the name without .xml. Example: windows_service_list_sql. Used only when "
                        "Guest OS Service Monitoring Status is Enabled, and it needs the Windows User Name and "
                        "Password in the credential. Clone the default file and list only the services you care "
                        "about, because each one is checked in every Windows VM.",
            default="windows_service_list",
            required=False,
            advanced=True
        )

        definition.define_string_parameter(
            "win_event_config_file",
            label="Windows Event Log Configuration File",
            description="The name of the configuration file that lists the Windows event logs and event IDs to "
                        "collect from guest VMs. Give the name without .xml. Example: windows_event_list_prod. "
                        "Used only when Windows Event Log Monitoring Status is Enabled, and it needs the Windows "
                        "credential. Clone the default file and keep the list short.",
            default="windows_event_list",
            required=False,
            advanced=True
        )

        definition.define_enum_parameter("serviceMonitoring",
            values=["Enabled", "Disabled"],
            label="Guest OS Service Monitoring Status",
            description="Enabled checks the services in the Windows Service Configuration File inside each "
                        "Windows VM, through VMware Tools, and publishes their state. Disabled (the default) skips "
                        "this. Turn it on only when the Windows User Name and Password are set in the credential, "
                        "because it runs a command in every Windows guest and adds to the collection time.",
            default="Disabled",
            required=False,
            advanced=True
        )

        definition.define_enum_parameter(
            constants.main.GUEST_TLS_VALIDATION,
            values=guest_http.GUEST_MODES,
            label="Guest File Transfer TLS Validation",
            description="Pinned (the default): the ESXi host certificate must match the thumbprint that vCenter "
                        "records for the host; when vCenter has none, the transfer goes ahead unchecked and the log "
                        "says so. Strict: as Pinned, but a host with no thumbprint is skipped. Disabled: nothing is "
                        "checked. Used only when Guest OS Service or Windows Event Log Monitoring is Enabled.",
            default=guest_http.DEFAULT_GUEST_MODE,
            required=False,
            advanced=True
        )

        definition.define_enum_parameter("winEventMonitoring",
            values=["Enabled", "Disabled"],
            label="Windows Event Log Monitoring Status",
            description="Enabled collects the events in the Windows Event Log Configuration File from each "
                        "Windows VM, through VMware Tools. Disabled (the default) skips this. It needs the Windows "
                        "User Name and Password in the credential.",
            default="Disabled",
            required=False,
            advanced=True
        )


        ### --- Adapter definitions --- ###

        # Credentials
        credential = definition.define_credential_type("vsphere_user", "vCenter Credential")
        credential.define_string_parameter(constants.main.USER_CREDENTIAL, "vCenter User Name")
        credential.define_password_parameter(constants.main.PASSWORD_CREDENTIAL, "vCenter Password")
        credential.define_string_parameter("winUser", "Windows User Name", required=False)
        credential.define_password_parameter("winPass", "Windows Password", required=False)


        # Cluster Compute Resource
        clusterComputeResource = definition.define_object_type("Cluster Compute Resource", "Cluster Compute Resource")
        vCommunity = clusterComputeResource.define_group("vCommunity", "vCommunity")
        clusterConfiguration = vCommunity.define_group("Cluster Configuration", "Cluster Configuration")

        clusterConfiguration.define_string_property("Configuration Status", "Configuration Status")
        clusterConfiguration.define_metric("Number of Effective Hosts", "Number of Effective Hosts")
        clusterConfiguration.define_string_property("Overall Status", "Overall Status")

        define_kpi(vCommunity, cluster_performance_metrics)
        define_kpi(vCommunity, cluster_risk_metrics)
        define_kpi(vCommunity, cluster_consumption_metrics)
        define_availability(vCommunity, cluster_availability.CLUSTER_METRIC)
        # Resource pools of the cluster, from VCF Operations: see metrics/cluster/resource_pool_counts.py.
        clusterResourcePools = vCommunity.define_group(resource_pool_counts.GROUP, resource_pool_counts.GROUP)
        clusterResourcePools.define_metric(resource_pool_counts.COUNT_METRIC, resource_pool_counts.COUNT_METRIC)
        clusterResourcePools.define_metric(resource_pool_counts.CASCADING_METRIC, resource_pool_counts.CASCADING_METRIC)

        # Periodic Cluster Check: set once per period. See metrics/cluster/periodic_cluster_check.py.
        periodicCheck = vCommunity.define_group(periodic_cluster_check.GROUP, periodic_cluster_check.GROUP)
        # Metrics, produced once per period. No properties: the metrics' timestamps say which window is done.
        for name in (periodic_cluster_check.PERFORMANCE, periodic_cluster_check.RISK, periodic_cluster_check.CONSUMPTION):
            periodicCheck.define_metric(name, name, unit=Units.RATIO.PERCENT)
        periodicCheck.define_metric(periodic_cluster_check.CLOSE_FOR_BUSINESS, periodic_cluster_check.CLOSE_FOR_BUSINESS)

        vSphereHA = clusterConfiguration.define_group("vSphere HA", "vSphere HA")
        vSphereHA.define_string_property("Host Monitoring", "Host Monitoring")
        vSphereHA.define_string_property("Host Isolation", "Response \\ Host Isolation")
        vSphereHA.define_string_property("Default VM Restart Priority", "Response \\ Default VM Restart Priority")
        vSphereHA.define_string_property("Datastore APD", "Response \\ Datastore APD")
        vSphereHA.define_string_property("Datastore PDL", "Response \\ Datastore PDL")
        vSphereHA.define_string_property("VM Monitoring", "VM Monitoring")
        vSphereHA.define_string_property("Heartbeat Datastore", "Heartbeat Datastore")
        vSphereHA.define_string_property("Failure Interval", "Failure Interval")
        vSphereHA.define_string_property("Max Failure Window", "Max Failure Window")
        vSphereHA.define_string_property("Max Failures", "Max Failures")
        vSphereHA.define_string_property("Minimum Up Time", "Minimum Up Time")

        drs = clusterConfiguration.define_group("Distributed Resource Scheduler", "Distributed Resource Scheduler")
        drs.define_string_property("Proactive DRS", "Proactive DRS")
        drs.define_string_property("Scale Descendants Shares", "Scale Descendants Shares")
        drs.define_string_property("CPU Over-Commitment","CPU Over-Commitment")
        drs.define_string_property("Virtual Machine Automation Enabled","Virtual Machine Automation Enabled")
        drs.define_metric("DRS Score", "DRS Score")

        evc = clusterConfiguration.define_group("EVC", "EVC")
        evc.define_string_property("Enabled", "Enabled")
        evc.define_string_property("Mode", "Mode")

        dpm = clusterConfiguration.define_group("DPM", "DPM")
        dpm.define_string_property("Host Power Action Rate", "Host Power Action Rate")


        # Host System
        hostSystem = definition.define_object_type("Host System", "Host System")
        vCommunity = hostSystem.define_group("vCommunity", "vCommunity")
        hostSystemConfiguration = vCommunity.define_group("Configuration", "Configuration")

        define_kpi(vCommunity, esxi_performance_metrics)
        define_availability(vCommunity, host_availability.HOST_METRIC)

        hostSystemConfiguration.define_string_property("Config Status", "Config Status")
        hostSystemConfiguration.define_string_property("Max EVC", "Max EVC")
        
        hostVAAI = hostSystemConfiguration.define_group("VAAI", "VAAI")
        hostVAAI.define_string_property("ATS Heartbeat", "ATS Heartbeat")
        hostVAAI.define_string_property("ATS Locking", "ATS Locking")

        hostTimeZone = hostSystemConfiguration.define_group("Time Zone", "Time Zone")
        hostTimeZone.define_string_property("Time Zone Name", "Time Zone Name")
        hostTimeZone.define_string_property("Description", "Description")
        hostTimeZone.define_string_property("GMT Offset", "GMT Offset")

        advancedSystemSettings = hostSystemConfiguration.define_group("AdvancedSystemSettings", "Advanced System Settings")
        advancedSystemSettings.define_string_property("Key", "Key")

        licensing = vCommunity.define_group("Licensing", "Licensing")
        licensing.define_string_property("License Name", "License Name")
        licensing.define_string_property("License Key", "License Key")
        licensing.define_string_property("License Expiration Date", "License Expiration Date")
        licensing.define_metric("Remaining Days", "Remaining Days")
        licensing.define_string_property("Edition Key", "Edition Key")

        installDate = hostSystemConfiguration.define_group("Install Date", "Install Date")
        installDate.define_string_property("UTC", "UTC")

        packages = hostSystemConfiguration.define_instanced_group("Packages", "Packages", instance_required=True)
        packages.define_string_property("Package Name", "Package Name")
        packages.define_string_property("Package Version", "Package Version")
        packages.define_string_property("Acceptance Level", "Acceptance Level")
        packages.define_string_property("Maintenance Mode Required", "Maintenance Mode Required")
        packages.define_string_property("Package Summary", "Package Summary")
        packages.define_string_property("Package Type", "Package Type")
        packages.define_string_property("Package Vendor", "Package Vendor")

        hostSystemNetwork = vCommunity.define_group("Network", "Network")
        hostSystemNetwork.define_string_property("DHCP", "DHCP")
        hostSystemNetwork.define_metric(host_network_speed.HOST_METRIC, host_network_speed.HOST_METRIC, unit=Units.RATIO.PERCENT)
        hostSystemNetwork.define_string_property("Search Domain", "Search Domain")

        networkDevice = hostSystemNetwork.define_instanced_group("Host Network Device", "Host Network Device", instance_required=True)
        networkDevice.define_string_property("Host Network Device Device Name", "Host Network Device Device Name")
        networkDevice.define_string_property("Host Network Device Driver Version", "Host Network Device Driver Version")
        networkDevice.define_string_property("Host Network Device Firmware Version", "Host Network Device Firmware Version")
        networkDevice.define_string_property("Host Network Device Status", "Host Network Device Status")
        networkDevice.define_string_property("PCI Vendor Name", "PCI Vendor Name")
        networkDevice.define_string_property("PCI Device Name", "PCI Device Name")
        networkDevice.define_string_property("PCI Vendor ID (VID)", "PCI Vendor ID (VID)")
        networkDevice.define_string_property("PCI Device ID (DID)", "PCI Device ID (DID)")
        networkDevice.define_string_property("PCI SubVendor ID (SVID)", "PCI SubVendor ID (SVID)")
        networkDevice.define_string_property("Host Network Device MAC", "Host Network Device MAC")
        networkDevice.define_string_property("Wake On Lan Supported", "Wake On Lan Supported")
        networkDevice.define_string_property("Host Network Device PCI", "Host Network Device PCI")
        networkDevice.define_string_property("Host Network Device Duplex", "Host Network Device Duplex")

        storageAdapter = vCommunity.define_group("Storage Adapter", "Storage Adapter")
        storageAdapter.define_string_property("Number of HBA", "Number of HBA")

        hbaDevice = storageAdapter.define_instanced_group("hbaDevice", "hbaDevice", instance_required=True)
        hbaDevice.define_string_property("HBA Device", "HBA Device")
        hbaDevice.define_string_property("HBA Device Bus", "HBA Device Bus")
        hbaDevice.define_string_property("HBA Device Model", "HBA Device Model")
        hbaDevice.define_string_property("HBA Device PCI", "HBA Device PCI")
        hbaDevice.define_string_property("HBA Device Status", "HBA Device Status")
        hbaDevice.define_string_property("HBA Device Type", "HBA Device Type")

        hostRuntime = vCommunity.define_group("Runtime", "Runtime")
        hostRuntime.define_string_property("Host Boot Time", "Host Boot Time")

        hostCapability = vCommunity.define_group("Capability", "Capability")
        hostCapability.define_string_property("Storage vMotion Supported", "Storage vMotion Supported")

        hostHardware = vCommunity.define_group("Hardware", "Hardware")
        hostHardware.define_string_property("Host BIOS Vendor", "Host BIOS Vendor")


        #TODO fix the object definition below
        # Datastore
        datastore = definition.define_object_type("vCommunity-Datastore", "Datastore")
        vCommunity = datastore.define_group("vCommunity", "vCommunity")

        datastoreIdentifiers = vCommunity.define_group("Identifiers", "Identifiers")
        datastoreIdentifiers.define_string_property("Number of Extents", "Number of Extents")

        datastoreExtents = datastoreIdentifiers.define_instanced_group("Extent", "Extent")
        datastoreExtents.define_string_property("Datastore Extent ID", "ID")

        datastoreSummary = vCommunity.define_group("Summary", "Summary")
        datastoreSummary.define_string_property("DS MOID", "MOID")
        datastoreSummary.define_string_property("DS Block Size", "Block Size")
        datastoreSummary.define_string_property("DS ax Blocks", "Max Blocks")
        datastoreSummary.define_string_property("DS VMFS Upgradable", "VMFS Upgradable")
        datastoreSummary.define_string_property("DS Status", "Status")
        datastoreSummary.define_string_property("DS SIOC Enabled", "SIOC Enabled")
        datastoreSummary.define_string_property("DS SIOC Threshold", "SIOC Threshold")


        # Virtual Machine
        virtualMachine = definition.define_object_type("Virtual Machine", "Virtual Machine")
        vCommunity = virtualMachine.define_group("vCommunity", "vCommunity")
        configuration = vCommunity.define_group("Configuration", "Configuration")

        define_kpi(vCommunity, vm_performance_metrics)
        define_kpi(vCommunity, guest_os_performance_metrics)
        # The average of the two KPIs above. See metrics/vm/vm_guest_os_kpi.py.
        vCommunity.define_metric(vm_guest_os_kpi.KPI_KEY, vm_guest_os_kpi.KPI_KEY, unit=Units.RATIO.PERCENT)

        configuration.define_string_property("CPU Allocation Share Level", "CPU Allocation Share Level")
        # Normalized shares. Metrics for now, though they should be properties: see properties/vm/vm_shares.py and issue #49.
        configuration.define_metric(vm_shares.CPU_METRIC, vm_shares.CPU_METRIC)
        configuration.define_metric(vm_shares.MEMORY_METRIC, vm_shares.MEMORY_METRIC)
        configuration.define_string_property("VM Change Version", "VM Change Version")
        configuration.define_string_property("VM Firmware", "VM Firmware")
        configuration.define_string_property("VM Latency Sensitivity Level", "VM Latency Sensitivity Level")
        configuration.define_string_property("VM Reboot PowerOff", "VM Reboot PowerOff")
        configuration.define_string_property("VM Op Notification Timeout", "VM Op Notification Timeout")
        configuration.define_string_property("VM Memory Allocation Share Level", "VM Memory Allocation Share Level")
        configuration.define_string_property("VM Config Status", "VM Config Status")
        
        vmNUMA = configuration.define_group("NUMA", "NUMA")
        vmNUMA.define_string_property("VM Hot Add Exposed", "VM Hot Add Exposed")

        vmBootOptions = configuration.define_group("Boot Options", "Boot Options")
        vmBootOptions.define_string_property("VM Boot Delay", "VM Boot Delay")
        vmBootOptions.define_string_property("VM Boot Retry Delay", "VM Boot Retry Delay")
        vmBootOptions.define_string_property("VM Boot Retry Enabled", "VM Boot Retry Enabled")
        vmBootOptions.define_string_property("VM Boot Enter BIOS Setup", "VM Boot Enter BIOS Setup")

        vmHWUpgrade = configuration.define_group("Hardware", "Hardware")
        vmHWUpgrade.define_string_property("VM HW Upgrade Status", "VM HW Upgrade Status")
        vmHWUpgrade.define_string_property("VM HW Upgrade Policy", "VM HW Upgrade Policy")
        vmHWUpgrade.define_string_property("VM HW Upgrade Target Version", "VM HW Upgrade Target Version")

        vmGuest = vCommunity.define_group("Guest", "Guest")
        vmGuest.define_string_property("State", "State")
        vmGuest.define_string_property("Application Status", "Application Status")
        vmGuest.define_string_property("Kernel Crash State", "Kernel Crash State")
        vmGuest.define_string_property("Operation Ready", "Operation Ready")
        vmGuest.define_string_property("State Change Support", "State Change Support")
        vmGuest.define_string_property("Interactive Guest", "Interactive Guest")
        vmGuest.define_string_property("Tools Sync Time", "Tools Sync Time")
        vmGuest.define_string_property("Tools Upgrade Policy", "Tools Upgrade Policy")
        vmGuest.define_string_property("Customization Status", "Customization Status")
        vmGuest.define_string_property("Heartbeat Status", "Heartbeat Status")

        vmGuestDetailed = vmGuest.define_group("Detailed Data", "Detailed Data")
        vmGuestDetailed.define_string_property("Build Number", "Build Number")
        vmGuestDetailed.define_string_property("CPE String", "CPE String")
        vmGuestDetailed.define_string_property("Distro Additional Version", "Distro Additional Version")
        vmGuestDetailed.define_string_property("Distro Name", "Distro Name")
        vmGuestDetailed.define_string_property("Distro Version", "Distro Version")
        vmGuestDetailed.define_string_property("Kernel Version", "Kernel Version")
        vmGuestDetailed.define_string_property("Pretty Name", "Pretty Name")

        vmRuntime = vCommunity.define_group("Runtime", "Runtime")
        vmRuntime.define_string_property("Consolidation Needed", "Consolidation Needed")
        vmRuntime.define_string_property("DAS protection", "DAS protection")
        vmRuntime.define_string_property("Min Required EVC Mode Key", "Min Required EVC Mode Key")

        vmFlags = configuration.define_group("Flags", "Flags")
        vmFlags.define_string_property("Disk UUID Enabled", "Disk UUID Enabled")

        advancedParameters = configuration.define_group("Advanced Parameters", "Advanced Parameters")
        advancedParameters.define_string_property("Parameter Key", "Parameter Key")

        scsiControllers = configuration.define_instanced_group("SCSI Controllers", "SCSI Controllers")
        scsiControllers.define_string_property("SCSI Controller Type", "SCSI Controller Type")
        scsiControllers.define_metric("SCSI Controllers Count", "Count")

        options = vCommunity.define_group("Options", "Options")
        options.define_string_property("Option Key", "Option Key")

        vmNetwork = vCommunity.define_group("Network", "Network")
        vmNetworkAdapters = vmNetwork.define_instanced_group("Network Adapters", "Network Adapters")
        vmNetworkAdapters.define_string_property("Network Adapter Type", "Network Adapter Type")
        vmNetworkAdapters.define_string_property("Starts Connected", "Starts Connected")

        vmSummary = vCommunity.define_instanced_group("Summary", "Summary")
        vmSummary.define_string_property("VM Path Name", "VM Path Name")

        vmVirtualDisk = vCommunity.define_instanced_group("Virtual Disk", "Virtual Disk")
        vmVirtualDisk.define_string_property("Label", "Label")
        vmVirtualDisk.define_string_property("Key", "Key")
        vmVirtualDisk.define_string_property("Controller Key", "Controller Key")
        vmVirtualDisk.define_string_property("Eagerly Scrub", "Eagerly Scrub")
        vmVirtualDisk.define_string_property("Split", "Split")
        vmVirtualDisk.define_string_property("Write Through", "Write Through")
        vmVirtualDisk.define_string_property("Storage Allocation Share Level", "Storage Allocation Share Level")

        guestOS = vCommunity.define_group("Guest OS", "Guest OS")
        services = guestOS.define_instanced_group("Services", "Services")
        services.define_string_property("Service Name", "Service Name")
        services.define_string_property("Service Status", "Service Status")
        services.define_string_property("Service Start Type", "Service Start Type")

        operatingSystem = guestOS.define_group("Operating System", "Operating System")
        operatingSystem.define_string_property("OS Name", "OS Name")
        operatingSystem.define_string_property("OS Version", "OS Version")
        operatingSystem.define_string_property("OS BuildNumber", "OS BuildNumber")
        operatingSystem.define_string_property("OS Architecture", "OS Architecture")
        operatingSystem.define_string_property("OS Last Boot Up Time", "OS Last Boot Up Time")
        operatingSystem.define_string_property("OS Release ID", "OS Release ID")


        # vSphere World: the cluster summary metrics, over the clusters of all vCenters.
        vSphereWorld = definition.define_object_type("vSphere World", "vSphere World")
        vCommunity = vSphereWorld.define_group("vCommunity", "vCommunity")
        for name in cluster_summary_metrics.METRICS:
            vCommunity.define_metric(name, name, unit=Units.RATIO.PERCENT)
        define_availability(vCommunity, vcenter_availability.WORST_CLUSTER_METRIC, availability_summary_metrics.HOSTS_METRIC)
        define_network_count(vCommunity)
        # Close for Business changes between two Periodic Cluster Check windows: counts of clusters.
        vCommunity.define_metric(cluster_close_changes.CLOSE_COUNT, cluster_close_changes.CLOSE_COUNT)
        vCommunity.define_metric(cluster_close_changes.OPEN_COUNT, cluster_close_changes.OPEN_COUNT)
        # Port groups of every kind, and VMware Tools across all VMs: counts of objects.
        vCommunity.define_metric(port_group_counts.METRIC, port_group_counts.METRIC)
        vCommunity.define_metric(vm_tools_counts.WITHOUT_METRIC, vm_tools_counts.WITHOUT_METRIC)
        vCommunity.define_metric(vm_tools_counts.DOWN_METRIC, vm_tools_counts.DOWN_METRIC)

        # Business Application performance on the Container objects, in percent. The object types are defined here so
        # that VCF Operations shows the unit. See metrics/container/business_app_performance.py.
        for kind, label, metric in business_app_performance.DEFINED_ON:
            container_object = definition.define_object_type(kind, label)
            vCommunity = container_object.define_group("vCommunity", "vCommunity")
            group = vCommunity.define_group(business_app_performance.GROUP, business_app_performance.GROUP)
            group.define_metric(metric, metric, unit=Units.RATIO.PERCENT)

        # Datacenter: the number of hosts with Network Speed Degradation.
        datacenter = definition.define_object_type("Datacenter", "Datacenter")
        define_network_count(datacenter.define_group("vCommunity", "vCommunity"))

        # vCenter
        vCenter = definition.define_object_type("vCenter", "vCenter")
        vCommunity = vCenter.define_group("vCommunity", "vCommunity")
        vCenterConfiguration = vCommunity.define_group("Configuration", "Configuration")
        define_availability(vCommunity, vcenter_availability.WORST_CLUSTER_METRIC)

        # Number of Port Groups of this vCenter, summed on vSphere World: see metrics/vcenter/vcenter_port_groups.py.
        vCommunity.define_metric(vcenter_port_groups.METRIC, vcenter_port_groups.METRIC)

        # Collection warnings of this vCenter's last cycle, for the Collection Warnings alert. See utils/collection_health.py.
        vCenterCollectionHealth = vCommunity.define_group(collection_health.GROUP, collection_health.GROUP)
        vCenterCollectionHealth.define_metric(collection_health.WARNINGS_METRIC, collection_health.WARNINGS_METRIC)
        vCenterCollectionHealth.define_string_property(collection_health.FIRST_WARNING_PROPERTY, collection_health.FIRST_WARNING_PROPERTY)

        # Trust on First Use of the vCenter certificate: see properties/vcenter/certificate.py.
        vCenterCertificate = vCommunity.define_group("Certificate", "Certificate")
        vCenterCertificate.define_string_property("SHA-256 Thumbprint", "SHA-256 Thumbprint")
        vCenterCertificate.define_string_property("Status", "Status")
        vCenterCertificate.define_string_property("Previous SHA-256 Thumbprint", "Previous SHA-256 Thumbprint")
        vCenterCertificate.define_string_property("Last Changed", "Last Changed")

        vCenterConfiguration.define_string_property("Patch Level", "Patch Level")
        vCenterConfiguration.define_string_property("User Directory Timeout", "User Directory Timeout")
        vCenterConfiguration.define_string_property("Enable MOB", "Enable MOB")
        vCenterConfiguration.define_string_property("Log Level", "Log Level")

        vCenterDatabase = vCenterConfiguration.define_group("Database", "Database")
        vCenterDatabase.define_string_property("Event retention (days)", "Event retention (days)")
        vCenterDatabase.define_string_property("Event Cleanup Enabled", "Event Cleanup Enabled")
        vCenterDatabase.define_string_property("Task retention (days)", "Task retention (days)")
        vCenterDatabase.define_string_property("Task Cleanup Enabled", "Task Cleanup Enabled")

        vCenterDatabaseRuntime = vCenterConfiguration.define_group("Runtime", "Runtime")
        vCenterDatabaseRuntime.define_string_property("vCenter Unique ID", "vCenter Unique ID")
        vCenterDatabaseRuntime.define_string_property("vCenter managed address", "vCenter managed address")
        vCenterDatabaseRuntime.define_string_property("Maximum Connections", "Maximum Connections")

        # Content Library: one per library of a vCenter, local or subscribed. See collectors/library/collectLibraryData.py.
        contentLibrary = definition.define_object_type(LIBRARY_KIND, LIBRARY_KIND)
        contentLibrary.define_string_identifier(LIBRARY_ID_KEY, LIBRARY_ID_KEY)
        libraryGroup = contentLibrary.define_group("vCommunity", "vCommunity").define_group(LIBRARY_KIND, LIBRARY_KIND)
        for name in ("Type", "Subscription URL", "Automatic Sync", "State"):
            libraryGroup.define_string_property(name, name)
        for name in ("Items", "Items Not Stored Locally", "Items Not Security Compliant"):
            libraryGroup.define_metric(name, name)
        libraryGroup.define_metric("Total Size (GB)", "Total Size (GB)")

        # Library Item: one per item of every type (OVF, OVA, VM template, ISO and others), with Type as a property.
        libraryItem = definition.define_object_type(ITEM_KIND, ITEM_KIND)
        libraryItem.define_string_identifier(ITEM_ID_KEY, ITEM_ID_KEY)
        itemGroup = libraryItem.define_group("vCommunity", "vCommunity").define_group(ITEM_KIND, ITEM_KIND)
        for name in ("Type", "Description", "Version", "Content Version", "Stored Locally", "Security Compliant",
                     "Certificate Verification", "Last Modified", "Last Sync", "Source Item ID"):
            itemGroup.define_string_property(name, name)
        itemGroup.define_metric("Size (GB)", "Size (GB)")

        # VM Template: a VM marked as a template, with the Virtual Machine Folder it sits in as its parent.
        # See collectors/library/collectTemplateData.py.
        vmTemplate = definition.define_object_type(TEMPLATE_KIND, TEMPLATE_KIND)
        vmTemplate.define_string_identifier("VMEntityObjectID", "VMEntityObjectID")
        vmTemplate.define_string_identifier("VMEntityVCID", "VMEntityVCID")
        templateGroup = vmTemplate.define_group("vCommunity", "vCommunity").define_group(TEMPLATE_KIND, TEMPLATE_KIND)
        for name in ("Guest OS", "Hardware Version", "vCPUs", "Memory (GB)", "Datastore", "VM Folder"):
            templateGroup.define_string_property(name, name)
        templateGroup.define_metric("Disk Used (GB)", "Disk Used (GB)")

        logger.debug(f"Returning adapter definition: {definition.to_json()}")

    return definition
