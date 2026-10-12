#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Who runs where, and how big it is: read from VCF Operations, for the KPIs.

The KPIs that score a host or a cluster need to know which VMs run on each host, which hosts are in each
cluster, how big the VMs are and how big the hosts are. VCF Operations already holds all of this as
properties, collected by its vCenter adapter, so it is read from there, once per collection cycle, for all
objects at once. Nothing is read from vCenter, so nothing is collected twice.

Placement is by name: a VM's summary|parentHost and a host's summary|parentCluster hold the name shown in
vCenter, not an id. Names are unique inside one datacenter, so do not mix datacenters in one adapter instance.
"""
from typing import Dict, List, NamedTuple, Optional
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from utils.ops_stats import OpsResource, query_resources, read_latest_properties, read_latest_stats, as_number


# --- VM properties ---
VM_PARENT_HOST = "summary|parentHost"           # name of the ESXi host the VM runs on
VM_POWER_STATE = "summary|runtime|powerState"
VM_VCPUS = "config|hardware|numCpu"
VM_MEMORY_KB = "config|hardware|memoryKB"
VM_PROPERTY_KEYS = [VM_PARENT_HOST, VM_POWER_STATE, VM_VCPUS, VM_MEMORY_KB]
POWERED_ON = "Powered On"

# --- ESXi host properties ---
HOST_PARENT_CLUSTER = "summary|parentCluster"   # name of the cluster the host is in
HOST_CORES = "hardware|cpuInfo|numCpuCores"     # physical cores, not threads
HOST_HYPERTHREAD_ACTIVE = "config|hyperThread|active"
HOST_HYPERTHREAD_AVAILABLE = "config|hyperThread|available"
HOST_PROPERTY_KEYS = [HOST_PARENT_CLUSTER, HOST_CORES, HOST_HYPERTHREAD_ACTIVE, HOST_HYPERTHREAD_AVAILABLE]


class VmInfo(NamedTuple):
    id: str                     # VCF Operations resource id
    name: str
    moid: str                   # vCenter MoRef id, to find the SDK object of the VM
    host_name: Optional[str]    # the ESXi host it runs on
    powered_on: bool
    vcpus: Optional[float]
    memory_mb: Optional[float]


class HostInfo(NamedTuple):
    id: str                     # VCF Operations resource id
    name: str
    moid: str                   # vCenter MoRef id, to find the SDK object of the host
    cluster_name: Optional[str]
    cores: Optional[float]      # physical cores
    threads: Optional[float]    # CPU threads: twice the cores with hyper-threading on, the cores without


def read_vms(suite_api_client: SuiteApiClient, adapter_instance_id: str) -> List[VmInfo]:
    """Every VM of the adapter instance, with its host, power state and size."""
    vms = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "VirtualMachine", adapter_instance_id)
    properties = read_latest_properties(suite_api_client, [vm.id for vm in vms], VM_PROPERTY_KEYS)
    return [vm_info(vm, properties.get(vm.id, {})) for vm in vms]


def vm_info(vm: OpsResource, properties: Dict[str, str]) -> VmInfo:
    memory_kb = as_number(properties.get(VM_MEMORY_KB))
    return VmInfo(
        id=vm.id,
        name=vm.name,
        moid=vm.moid,
        host_name=properties.get(VM_PARENT_HOST),
        powered_on=properties.get(VM_POWER_STATE) == POWERED_ON,
        vcpus=as_number(properties.get(VM_VCPUS)),
        memory_mb=memory_kb / 1024.0 if memory_kb is not None else None,
    )


def read_hosts(suite_api_client: SuiteApiClient, adapter_instance_id: str) -> List[HostInfo]:
    """Every ESXi host of the adapter instance, with its cluster, cores and threads."""
    hosts = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "HostSystem", adapter_instance_id)
    properties = read_latest_properties(suite_api_client, [host.id for host in hosts], HOST_PROPERTY_KEYS)
    return [host_info(host, properties.get(host.id, {})) for host in hosts]


def host_info(host: OpsResource, properties: Dict[str, str]) -> HostInfo:
    cores = as_number(properties.get(HOST_CORES))
    return HostInfo(
        id=host.id,
        name=host.name,
        moid=host.moid,
        cluster_name=properties.get(HOST_PARENT_CLUSTER),
        cores=cores,
        threads=threads(cores, properties),
    )


def threads(cores: Optional[float], properties: Dict[str, str]) -> Optional[float]:
    """Twice the cores when hyper-threading is both available and active, otherwise the cores.

    VCF Operations stores both properties as the text "true" or "false", not as 1 or 0.
    """
    if cores is None:
        return None
    hyperthreading = (properties.get(HOST_HYPERTHREAD_AVAILABLE, "").lower() == "true"
                      and properties.get(HOST_HYPERTHREAD_ACTIVE, "").lower() == "true")
    return cores * 2 if hyperthreading else cores


def powered_on_vms_by_host(vms: List[VmInfo]) -> Dict[str, List[VmInfo]]:
    """{host name: its powered-on VMs}. A powered-off VM is left out: its last stats are old."""
    vms_by_host = {}
    for vm in vms:
        if vm.powered_on and vm.host_name:
            vms_by_host.setdefault(vm.host_name, []).append(vm)
    return vms_by_host


def hosts_by_cluster(hosts: List[HostInfo]) -> Dict[str, List[HostInfo]]:
    """{cluster name: its ESXi hosts}."""
    by_cluster = {}
    for host in hosts:
        if host.cluster_name:
            by_cluster.setdefault(host.cluster_name, []).append(host)
    return by_cluster


# ---------------------------------------------------------------------------
# Cluster size and vSphere HA failover level.
# ---------------------------------------------------------------------------

CLUSTER_HOST_COUNT = "summary|total_number_hosts"
# Host failures vSphere HA tolerates (N+k), as in the former "Clusters Availability" super metric.
# No value when HA is off, or when admission control uses a percentage or dedicated failover hosts.
CLUSTER_FAILOVER_LEVEL = "configuration|dasConfig|hostFailoverLevel"


class ClusterHa(NamedTuple):
    """Size and HA failover level of one cluster. None means "no data"."""
    host_count: Optional[float]         # N
    failover_level: Optional[float]     # k


def read_cluster_ha(suite_api_client: SuiteApiClient, clusters: List[OpsResource]) -> Dict[str, ClusterHa]:
    """{cluster name: ClusterHa}, in two requests for all clusters.

    The failover level is read as a stat, or as a property when VCF Operations stores it as one.
    """
    cluster_ids = [cluster.id for cluster in clusters]
    stats = read_latest_stats(suite_api_client, cluster_ids, [CLUSTER_HOST_COUNT, CLUSTER_FAILOVER_LEVEL])
    properties = read_latest_properties(suite_api_client, cluster_ids, [CLUSTER_FAILOVER_LEVEL])
    by_name = {}
    for cluster in clusters:
        cluster_stats = stats.get(cluster.id, {})
        failover_level = cluster_stats.get(CLUSTER_FAILOVER_LEVEL)
        if failover_level is None:
            failover_level = as_number(properties.get(cluster.id, {}).get(CLUSTER_FAILOVER_LEVEL))
        by_name[cluster.name] = ClusterHa(cluster_stats.get(CLUSTER_HOST_COUNT), failover_level)
    return by_name
