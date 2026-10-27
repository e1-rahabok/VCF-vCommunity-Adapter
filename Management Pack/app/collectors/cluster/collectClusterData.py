#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
from typing import Any
from typing import List
from typing import Optional
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.suite_api_client import SuiteApiClient
from utils.vi_property_collector import retrieve_properties
from constants.main import VCENTER_ADAPTER_KIND
from properties.cluster.ha_properties import collect_ha_properties
from properties.cluster.drs_properties import collect_drs_properties
from metrics.cluster.drs_metrics import collect_drs_metrics
from properties.cluster.evc_properties import collect_evc_properties
from properties.cluster.dpm_properties import collect_dpm_properties
from properties.cluster.cluster_configuration_properties import collect_cluster_configuration_properties
from metrics.cluster.cluster_performance_metrics import collect_cluster_performance_metrics
from metrics.cluster.cluster_risk_metrics import (
    collect_cluster_risk_metrics, HostInventory, MonsterVmSize, DEFAULT_MONSTER_VM,
)
from utils.ops_inventory import read_hosts, read_vms, powered_on_vms_by_host, hosts_by_cluster
from utils.ops_stats import query_resources, read_latest_stats
from metrics.vcenter.vcenter_availability import OperationalAvailability, NO_DATA
from metrics.cluster import cluster_availability, periodic_cluster_check, cluster_consumption_metrics, resource_pool_counts
from pyVmomi import vim

logger = logging.getLogger(__name__)

def collect_cluster_data(
    suite_api_client: SuiteApiClient,
    adapter_instance_id: str,
    result: CollectResult,
    content: Any,
    availability: OperationalAvailability = NO_DATA,
    check_time: Optional[str] = None,
    check_period: Optional[str] = None,
    monster_vm: MonsterVmSize = DEFAULT_MONSTER_VM,
    check_worst_percent: Optional[str] = None,
) -> None:
    
    propertyPaths: List[str] = []
    propertyPaths.append("summary")
    propertyPaths.append("configuration.dasConfig.enabled")
    propertyPaths.append("configuration.dasConfig.hostMonitoring")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.isolationResponse")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.restartPriority")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.vmComponentProtectionSettings.vmStorageProtectionForAPD")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.vmComponentProtectionSettings.vmStorageProtectionForPDL")
    propertyPaths.append("configuration.dasConfig.vmMonitoring")
    propertyPaths.append("configuration.dasConfig.hBDatastoreCandidatePolicy")
    propertyPaths.append("configuration.drsConfig.enabled")
    propertyPaths.append("configuration.drsConfig.enableVmBehaviorOverrides")
    propertyPaths.append("configurationEx")
    propertyPaths.append("configuration.drsConfig.scaleDescendantsShares")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.failureInterval")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.maxFailureWindow")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.maxFailures")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.minUpTime")
    propertyPaths.append("configurationEx")
    propertyPaths.append("configStatus")
    propertyPaths.append("summary.numEffectiveHosts")
    propertyPaths.append("overallStatus")

    cluster_props = retrieve_properties(content, vim.ClusterComputeResource, propertyPaths)

    # Retrieve object types from the VCF Operations
    clusters: List[Object] = suite_api_client.query_for_resources(
        {
            "adapterKind": [VCENTER_ADAPTER_KIND],
            "resourceKind": ["ClusterComputeResource"],
            "adapterInstanceId": [adapter_instance_id],
        }
    )

    # Match the VCF Operations objects with the related identifier
    clusters_by_uuid: dict[str, Object] = {
        cluster.get_identifier_value("VMEntityObjectID"): cluster for cluster in clusters
    }

    # KPIs: read from VCF Operations once, for all clusters, which hosts are in each cluster and which
    # powered-on VMs run on each host, with their sizes. See utils/ops_inventory.py.
    all_hosts = read_hosts(suite_api_client, adapter_instance_id)
    hosts_in_cluster = hosts_by_cluster(all_hosts)
    vms_on_host = powered_on_vms_by_host(read_vms(suite_api_client, adapter_instance_id))
    # The VCF Operations ids of the clusters, for the cluster stats of Cluster Consumption.
    try:
        ops_clusters = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "ClusterComputeResource", adapter_instance_id)
    except Exception as e:
        logger.warning(f"Failed to read the clusters from VCF Operations, so no Cluster Consumption - {repr(e)}")
        ops_clusters = []

    # The stats of Cluster Consumption that Cluster Risk does not read, one request each for all clusters and all
    # hosts: usable capacity per cluster {cluster name: {stat key: value}}, NVMe memory tier per host {host id: ...}.
    try:
        consumption_stats = read_latest_stats(
            suite_api_client, [cluster.id for cluster in ops_clusters], cluster_consumption_metrics.CLUSTER_STATS)
        consumption_stats_by_cluster = {cluster.name: consumption_stats.get(cluster.id, {}) for cluster in ops_clusters}
        tier_stats_by_host = read_latest_stats(
            suite_api_client, [host.id for host in all_hosts], cluster_consumption_metrics.HOST_STATS)
    except Exception as e:
        logger.warning(f"Failed to read the usable capacity and memory tier stats of Cluster Consumption - {repr(e)}")
        consumption_stats_by_cluster = {}
        tier_stats_by_host = {}

    # Number of Resource Pools and Cascading Resource Pools, from the pools' parents in VCF Operations. A read that
    # fails publishes nothing this cycle. A cluster without pools gets 0 when the read worked.
    try:
        pool_counts = resource_pool_counts.read_counts(suite_api_client, adapter_instance_id)
    except Exception as e:
        logger.warning(f"Failed to read the resource pools, so no Number of Resource Pools this cycle - {repr(e)}")
        pool_counts = None
    cluster_id_by_moid = {cluster.moid: cluster.id for cluster in ops_clusters}

    # Periodic Cluster Check: only the clusters due this cycle. See metrics/cluster/periodic_cluster_check.py.
    try:
        checks = periodic_cluster_check.read_periodic_cluster_check(
            suite_api_client, adapter_instance_id, check_time, period_setting=check_period,
            worst_percent_setting=check_worst_percent)
    except Exception as e:
        # A failure here must not stop the rest of the collection. The clusters stay due for the next cycle.
        logger.warning(f"Failed to read the Periodic Cluster Check - {repr(e)}")
        checks = {}

    for cluster_data in cluster_props:
        try:
            cluster_ref = cluster_data.obj
            cluster_moid = cluster_ref._moId

            cluster_obj = clusters_by_uuid.get(cluster_moid)
            if not cluster_obj:
                # If cluster object is not available in VCF Operations - skip it.
                continue

            prop_dict = {p.name: p.val for p in cluster_data.propSet}
            cluster_name = prop_dict.get("name", "Unknown")

            collect_ha_properties(cluster_obj, cluster_name, prop_dict)
            collect_drs_properties(cluster_obj, cluster_name, prop_dict)
            collect_evc_properties(cluster_obj, cluster_name, prop_dict)
            collect_drs_metrics(cluster_obj, cluster_name, prop_dict)
            collect_dpm_properties(cluster_obj, cluster_name, prop_dict)
            collect_cluster_configuration_properties(cluster_obj, cluster_name, prop_dict)

            # KPIs. Hosts are matched to the cluster by name, as VCF Operations shows it (summary|parentCluster).
            cluster_hosts = hosts_in_cluster.get(cluster_obj.get_key().name, [])
            cluster_vms = [vm for host in cluster_hosts for vm in vms_on_host.get(host.name, [])]
            collect_cluster_performance_metrics(
                cluster_obj, cluster_name,
                [vm.id for vm in cluster_vms], [host.id for host in cluster_hosts],
                suite_api_client,
            )

            hosts_inventory = [
                HostInventory(host.id, host.cores, host.threads, vms_on_host.get(host.name, []))
                for host in cluster_hosts
            ]
            stats_by_host = collect_cluster_risk_metrics(
                cluster_obj, cluster_name, hosts_inventory, suite_api_client, monster_vm)

            # Cluster Consumption, from the same host stats. See metrics/cluster/cluster_consumption_metrics.py.
            cluster_consumption_metrics.collect_cluster_consumption_metrics(
                cluster_obj, cluster_name, cluster_hosts, stats_by_host, tier_stats_by_host,
                consumption_stats_by_cluster.get(cluster_obj.get_key().name, {}))

            # Operational Availability, read once per cycle for the whole vCenter by the adapter.
            cluster_availability.publish(cluster_obj, availability.by_cluster.get(cluster_obj.get_key().name))

            periodic_cluster_check.publish(cluster_obj, checks.get(cluster_moid))

            if pool_counts is not None:
                resource_pool_counts.publish(cluster_obj, pool_counts.get(cluster_id_by_moid.get(cluster_moid), (0, 0)))

            result.add_object(cluster_obj)

        except Exception as e:
            logger.warning(f"Skipping Cluster data collection on {cluster_name} due to error: {repr(e)}")
            continue