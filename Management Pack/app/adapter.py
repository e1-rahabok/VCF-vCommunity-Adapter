#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

#import os
import sys
#import threading
import time
import json
import atexit
import xml.etree.ElementTree as ET
import concurrent
import constants.main
import aria.ops.adapter_logging as logging
from typing import Any
from typing import List
from typing import Optional
from collections import defaultdict
from aria.ops.adapter_instance import AdapterInstance
from aria.ops.definition.adapter_definition import AdapterDefinition
from aria.ops.definition.units import Units
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.result import EndpointResult
from aria.ops.result import TestResult
from aria.ops.suite_api_client import key_to_object
from aria.ops.suite_api_client import SuiteApiClient
from aria.ops.timer import Timer
from pyVim.connect import Disconnect
from pyVim.connect import SmartConnect
from utils import config_files
from utils import guest_args
from utils import guest_http
from utils import tls
from collectors.cluster.collectClusterData import collect_cluster_data
from collectors.host.collectHostData import collect_host_data
from collectors.vm.collectVMData import collect_vm_data
from collectors.datastore.collectDatastoreData import collect_datastore_data
from collectors.vcenter.collectvCenterData import collect_vcenter_data
from collectors.world.collectWorldData import collect_world_data
from collectors.datacenter.collectDatacenterData import collect_datacenter_data
from metrics.cluster import (
    cluster_performance_metrics, cluster_risk_metrics, cluster_consumption_metrics, periodic_cluster_check,
)
from metrics.host import esxi_performance_metrics, host_availability, host_network_speed
from metrics.vm import vm_performance_metrics, guest_os_performance_metrics, vm_guest_os_kpi
from properties.vm import vm_shares
from metrics.world import cluster_summary_metrics, availability_summary_metrics, cluster_close_changes
from metrics.world import port_group_counts, vm_tools_counts
from metrics.vcenter import vcenter_port_groups
from metrics.cluster import cluster_availability
from metrics.datacenter import datacenter_network_degradation
from metrics.vcenter import vcenter_availability
from metrics.vcenter.vcenter_availability import read_operational_availability
from metrics.vcenter.vcenter_network_speed import read_network_speed
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
timingLogger = logging.getLogger("[CollectionResult]")


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
        # Normalized shares, as properties: they change only with the VM configuration. See properties/vm/vm_shares.py.
        configuration.define_numeric_property(vm_shares.CPU_PROPERTY, vm_shares.CPU_PROPERTY)
        configuration.define_numeric_property(vm_shares.MEMORY_PROPERTY, vm_shares.MEMORY_PROPERTY)
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

        logger.debug(f"Returning adapter definition: {definition.to_json()}")

    return definition


def get_win_service_configFile(adapter_instance: AdapterInstance) -> str:
    win_service_config_file = adapter_instance.get_identifier_value("win_service_config_file")
    return win_service_config_file

def get_win_event_configFile(adapter_instance: AdapterInstance) -> str:
    configFile = adapter_instance.get_identifier_value("win_event_config_file")
    return configFile

def get_esxi_adv_settings_configFile(adapter_instance: AdapterInstance) -> str:
    esxiAdvSettingsConfigFile = adapter_instance.get_identifier_value("esxi_adv_settings_config_file")
    return esxiAdvSettingsConfigFile

def get_esxi_vib_driver_configFile(adapter_instance: AdapterInstance) -> str:
    esxi_vib_driver_config_file = adapter_instance.get_identifier_value("esxi_vib_driver_config_file")
    return esxi_vib_driver_config_file

def get_vm_adv_settings_configFile(adapter_instance: AdapterInstance) -> str:
    vm_adv_settings_config_file = adapter_instance.get_identifier_value("vm_adv_settings_config_file")
    return vm_adv_settings_config_file

def get_vm_configuration_configFile(adapter_instance: AdapterInstance) -> str:
    vm_configuration_config_file = adapter_instance.get_identifier_value("vm_configuration_config_file")
    return vm_configuration_config_file

def get_winCredential(adapter_instance: AdapterInstance) -> str:
    username = adapter_instance.get_credential_value("winUser")
    password = adapter_instance.get_credential_value("winPass")
    return username, password

def getServiceMonitoringStatus(adapter_instance: AdapterInstance) -> str:
    serviceMonitoringStatus = adapter_instance.get_identifier_value("serviceMonitoring")
    return serviceMonitoringStatus

def getWindowsEventLogMonitoringStatus(adapter_instance: AdapterInstance) -> str:
    WindowsEventLogMonitoringStatus = adapter_instance.get_identifier_value("winEventMonitoring")
    return WindowsEventLogMonitoringStatus    

def get_config_file_data(adapter_instance: AdapterInstance, configFile, problems: List[str]) -> List[str]:
    """The items of one configuration file. A file that cannot be read, or is not valid XML, gives [] for that file
    only, and its problem is added to problems. See utils/config_files.py."""
    apiPath = f"api/configurations/files?path=SolutionConfig/{configFile}.xml"

    with adapter_instance.suite_api_client as suite_api:
        getConfigFile = suite_api.get(url=apiPath)

    if not getConfigFile.ok:
        problems.append(config_files.missing_problem(configFile, getConfigFile.status_code))
        logger.warning(problems[-1])
        return []

    try:
        return config_files.parse_list(getConfigFile.text)
    except ET.ParseError as e:
        problems.append(config_files.invalid_problem(configFile, e.msg))
        logger.error(problems[-1])
        return []


TIMINGS = defaultdict(list)

def record_timing(operationName, duration):
    TIMINGS[operationName].append(duration)


def timingSummary():
    total = 0
    timingLogger.info("====================== Collection Timing Summary ======================")

    for operationName, duration_list in TIMINGS.items():
        if not duration_list:
            continue

        currentDuration = sum(duration_list)
        total += currentDuration
        
        if currentDuration < 60:
            timingLogger.info(f"Collection Operation: {operationName} > Duration: {currentDuration:.2f} seconds.")
        else:
            minutes = currentDuration / 60
            timingLogger.info(f"Collection Operation: {operationName} > Duration: {minutes:.2f} minutes.")

    timingLogger.info("=======================================================================")
    
    if total < 60:
        timingLogger.info(f"Total Collection Duration: {total:.2f} seconds.")
    else:
        total_minutes = total / 60
        timingLogger.info(f"Total Collection Duration: {total_minutes:.2f} minutes.")
        
    timingLogger.info("=======================================================================")


def test(adapter_instance: AdapterInstance) -> TestResult:
    with Timer(logger, "Test connection"):
        result = TestResult()
        try:
            logger.debug(f"Returning test result: {result.get_json()}")

            service_instance = _get_service_instance(adapter_instance)
            content = service_instance.RetrieveContent()
            logger.info(f"content: {content}")

        except Exception as e:
            logger.error("Unexpected connection test error")
            logger.exception(e)
            result.with_error("Unexpected connection test error: " + repr(e))
        finally:
            return result


def collect(adapter_instance: AdapterInstance) -> CollectResult:
    with Timer(logger, "Collection"):
        result = CollectResult()
        try:
            start_time = time.perf_counter()
            service_instance = _get_service_instance(adapter_instance)
            content = service_instance.RetrieveContent()
            # The certificate vCenter presents now, for the Trust on First Use comparison on the vCenter object
            # (properties/vcenter/certificate.py). Read in every mode, so the thumbprint is always visible.
            vcenter_certificate = tls.presented_thumbprint(
                adapter_instance.get_identifier_value(constants.main.HOST_IDENTIFIER),
                int(adapter_instance.get_identifier_value(constants.main.PORT_IDENTIFIER, 443)),
            )
            guest_http.configure(adapter_instance.get_identifier_value(constants.main.GUEST_TLS_VALIDATION))
            ServiceMonitoringStatus = getServiceMonitoringStatus(adapter_instance)
            WindowsEventLogMonitoringStatus = getWindowsEventLogMonitoringStatus(adapter_instance)
            winUser, winPassword = get_winCredential(adapter_instance)

            # Problems with the configuration files. Each one is published as an event on the vCenter object.
            config_problems: List[str] = []

            windowsEventConfigFile = get_win_event_configFile(adapter_instance)
            apiPath = f"api/configurations/files?path=SolutionConfig/{windowsEventConfigFile}.xml"
            with adapter_instance.suite_api_client as suite_api:
                getConfigFile = suite_api.get(url = apiPath)

            # The event list is passed to the Windows guest as it is, so it is checked here, not parsed.
            winEventLogConfigFile = ""
            if not getConfigFile.ok:
                config_problems.append(config_files.missing_problem(windowsEventConfigFile, getConfigFile.status_code))
                logger.warning(config_problems[-1])
            else:
                reason = config_files.check_xml(getConfigFile.text)
                if reason is None:
                    winEventLogConfigFile = getConfigFile.text
                else:
                    config_problems.append(config_files.invalid_problem(windowsEventConfigFile, reason))
                    logger.error(config_problems[-1])

            windowsServiceConfigFile = get_win_service_configFile(adapter_instance)
            windowsServices = guest_args.safe_service_names(
                get_config_file_data(adapter_instance, windowsServiceConfigFile, config_problems))

            esxiAdvSettingsConfigFile = get_esxi_adv_settings_configFile(adapter_instance)
            esxiAdvSettings = get_config_file_data(adapter_instance, esxiAdvSettingsConfigFile, config_problems)

            esxiVIBDriverConfigFile = get_esxi_vib_driver_configFile(adapter_instance)
            esxiVIBDrivers = get_config_file_data(adapter_instance, esxiVIBDriverConfigFile, config_problems)

            vmAdvParametersConfigFile = get_vm_adv_settings_configFile(adapter_instance)
            vmAdvParameters = get_config_file_data(adapter_instance, vmAdvParametersConfigFile, config_problems)

            vmConfigurationConfigFile = get_vm_configuration_configFile(adapter_instance)
            vmConfigs = get_config_file_data(adapter_instance, vmConfigurationConfigFile, config_problems)

            with adapter_instance.suite_api_client as client:
                adapter_instance_id = _get_vcenter_adapter_instance_id(
                    client, adapter_instance
                )
                if adapter_instance_id is None:
                    result.with_error(
                        f"No vCenter Adapter Instance found matching vCenter Server '{adapter_instance.get_identifier_value(constants.main.HOST_IDENTIFIER)}'"
                    )
                    return result
                
                duration = time.perf_counter() - start_time
                record_timing("main_collect", duration)

                # Operational Availability of the hosts and clusters of this vCenter. Read once here, because the
                # host, cluster and vCenter collections below all publish part of it.
                availability = read_operational_availability(client, adapter_instance_id)
                # Network Speed Degradation of the hosts of this vCenter, for the host and Datacenter collections.
                network_speed = read_network_speed(client, adapter_instance_id)

                start_times = {}

                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as data_executor:
                    
                    # 1. Cluster feature definition
                    start_times["collect_cluster_data"] = time.perf_counter()
                    future_cls = data_executor.submit(
                        collect_cluster_data, client, adapter_instance_id, result, content, availability,
                        adapter_instance.get_identifier_value(periodic_cluster_check.TIME_SETTING),
                        adapter_instance.get_identifier_value(periodic_cluster_check.PERIOD_SETTING),
                        cluster_risk_metrics.monster_vm_size(
                            adapter_instance.get_identifier_value(cluster_risk_metrics.MONSTER_CPU_SETTING),
                            adapter_instance.get_identifier_value(cluster_risk_metrics.MONSTER_MEMORY_SETTING),
                            adapter_instance.get_identifier_value(cluster_risk_metrics.MONSTER_MEMORY_MIN_SETTING),
                        ),
                        adapter_instance.get_identifier_value(periodic_cluster_check.WORST_PERCENT_SETTING),
                    )

                    # 2. Host feature definition
                    start_times["collect_host_data"] = time.perf_counter()
                    future_host = data_executor.submit(
                        collect_host_data, client, adapter_instance_id, result, content, esxiAdvSettings, esxiVIBDrivers,
                        availability, network_speed
                    )

                    # 3. VM feature definition
                    start_times["collect_vm_data"] = time.perf_counter()
                    future_vm = data_executor.submit(
                        collect_vm_data, client, adapter_instance_id, result, content, 
                        ServiceMonitoringStatus, WindowsEventLogMonitoringStatus, winUser, winPassword, 
                        winEventLogConfigFile, vmConfigs, vmAdvParameters, windowsServices
                    )

                    # 4. Datastore feature definition
                    start_times["collect_datastore_data"] = time.perf_counter()
                    future_ds = data_executor.submit(
                        collect_datastore_data, client, adapter_instance_id, result, content
                    )

                    # 5. vCenter feature definition
                    start_times["collect_vcenter_data"] = time.perf_counter()
                    future_vc = data_executor.submit(
                        collect_vcenter_data, client, adapter_instance_id, result, content, availability,
                        vcenter_certificate,
                        adapter_instance.get_identifier_value(constants.main.HOST_IDENTIFIER),
                        config_problems,
                    )

                    # 6. vSphere World: cluster summary metrics, over the clusters of all vCenters
                    start_times["collect_world_data"] = time.perf_counter()
                    future_world = data_executor.submit(
                        collect_world_data, client, result,
                        adapter_instance.get_identifier_value(periodic_cluster_check.TIME_SETTING),
                        adapter_instance.get_identifier_value(periodic_cluster_check.PERIOD_SETTING),
                    )

                    # 7. Datacenter: Total Network Speed Degradation of this vCenter's Datacenters
                    start_times["collect_datacenter_data"] = time.perf_counter()
                    future_dc = data_executor.submit(collect_datacenter_data, client, adapter_instance_id, result, network_speed)

                    # Define main futures
                    main_futures = [future_cls, future_host, future_vm, future_ds, future_vc, future_world, future_dc]
    
                    for future in concurrent.futures.as_completed(main_futures):
                        # Check future function
                        if future == future_cls:
                            func_name = "collect_cluster_data"
                        elif future == future_ds:
                            func_name = "collect_datastore_data"
                        elif future == future_vc:
                            func_name = "collect_vcenter_data"
                        elif future == future_host:
                            func_name = "collect_host_data"
                        elif future == future_world:
                            func_name = "collect_world_data"
                        elif future == future_dc:
                            func_name = "collect_datacenter_data"
                        else:
                            func_name = "collect_vm_data"

                        try:
                            future.result()
                            duration = time.perf_counter() - start_times[func_name]
                            record_timing(func_name, duration)
                            
                            logger.info(f"Finished {func_name} collection successfully.")
                            
                        except Exception as exc:
                            logger.error(f"Main data collection thread error in {func_name}: {exc}")
                            
                logger.info(f"Finished total data collection.")

        except Exception as e:
            logger.error("Unexpected collection error")
            logger.exception(e)
            result.with_error("Unexpected collection error: " + repr(e))
        finally:
            timingSummary()
            return result


def get_endpoints(adapter_instance: AdapterInstance) -> EndpointResult:
    with Timer(logger, "Get Endpoints"):
        result = EndpointResult()
        logger.debug(f"Returning endpoints: {result.get_json()}")
        return result


def _get_service_instance(
    adapter_instance: AdapterInstance,
) -> Any:
    host = adapter_instance.get_identifier_value(constants.main.HOST_IDENTIFIER)
    port = int(adapter_instance.get_identifier_value(constants.main.PORT_IDENTIFIER, 443))
    user = adapter_instance.get_credential_value(constants.main.USER_CREDENTIAL)
    password = adapter_instance.get_credential_value(constants.main.PASSWORD_CREDENTIAL)

    tls_args = tls.vcenter_connect_args(
        adapter_instance.get_identifier_value(constants.main.VCENTER_TLS_VALIDATION),
        adapter_instance.get_identifier_value(constants.main.VCENTER_THUMBPRINT),
    )

    try:
        service_instance = SmartConnect(host=host, port=port, user=user, pwd=password, **tls_args)
    except Exception as exc:
        explanation = tls.explain_connect_error(exc, host)
        if explanation:
            raise ConnectionError(explanation) from exc
        raise

    atexit.register(Disconnect, service_instance)

    return service_instance


def _get_vcenter_adapter_instance_id(
    client: SuiteApiClient, adapter_instance: Object
) -> Optional[str]:
    ais: List[Object] = client.query_for_resources(
        {
            "adapterKind": [constants.main.VCENTER_ADAPTER_KIND],
            "resourceKind": ["VMwareAdapter Instance"],
        }
    )
    vcenter_server = adapter_instance.get_identifier_value(constants.main.HOST_IDENTIFIER)
    for ai in ais:
        logger.debug(
            f"Considering vCenter Adapter Instance with VCURL: {ai.get_identifier_value('VCURL')}"
        )
        if ai.get_identifier_value("VCURL") == vcenter_server:
            return _get_adapter_instance_id(client, ai)
    return None


def _get_adapter_instance_id(
    client: SuiteApiClient, adapter_instance: Object
) -> Optional[Any]:
    response = client.get(
        f"api/adapters?adapterKindKey={adapter_instance.get_key().adapter_kind}"
    )
    if response.status_code < 300:
        for ai in json.loads(response.content).get("adapterInstancesInfoDto", []):
            adapter_instance_key = key_to_object(ai.get("resourceKey")).get_key()
            if adapter_instance_key == adapter_instance.get_key():
                return ai.get("id")
    return None


def main(argv: List[str]) -> None:
    logging.setup_logging("adapter.log")
    logging.rotate()
    logger.info(f"Running adapter code with arguments: {argv}")
    if len(argv) != 3:
        logger.error("Arguments must be <method> <inputfile> <ouputfile>")
        exit(1)

    method = argv[0]

    if method == "test":
        test(AdapterInstance.from_input()).send_results()
    elif method == "endpoint_urls":
        get_endpoints(AdapterInstance.from_input()).send_results()
    elif method == "collect":
        collect(AdapterInstance.from_input()).send_results()
    elif method == "adapter_definition":
        result = get_adapter_definition()
        if type(result) is AdapterDefinition:
            result.send_results()
        else:
            logger.info(
                "get_adapter_definition method did not return an AdapterDefinition"
            )
            exit(1)
    else:
        logger.error(f"Command {method} not found")
        exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])