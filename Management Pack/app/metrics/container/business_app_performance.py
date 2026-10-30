#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Business Application performance, on the Container objects: Tier, Business Application and Enterprise.

Three 0-100 % metrics, the calculations of the former super metrics, now in code:

    Tier Performance                  average of the VM Guest OS KPI of the Tier's VMs
    Business Application Performance  the higher of two values: the Performance of its K8S Namespaces, and the
                                      lowest Tier Performance of its Tiers
    Business Applications Performance average of the Business Applications of the Enterprise

A value is published only when it has data. A Tier whose VMs have no VM Guest OS KPI (all powered off, or no data)
publishes nothing, not 0. A Business Application uses the Tiers that have a value. An Enterprise uses the
Business Applications that have a value. A value is based on the stats of the last cycle, as the other
world-level metrics are, because the VM KPI of this cycle is stored only at the end of it.

The objects and their relationships are read from VCF Operations, not from vCenter. Each Business Application
is a parent of its Tiers (CHILD relationship), and a Tier is a parent of its VMs. The K8S Namespaces are found
within two levels of a Business Application, as the super metric's depth 2 did.
"""
import logging
from typing import Dict, List, Optional
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.suite_api_client import SuiteApiClient, key_to_object
from utils.ops_stats import RESOURCES_QUERY_PATH, Related, read_latest_stats, read_related

logger = logging.getLogger(__name__)

GROUP = "Business Application"
TIER_METRIC = "Tier Performance"
APPLICATION_METRIC = "Business Application Performance"
ENTERPRISE_METRIC = "Business Applications Performance"

CONTAINER_ADAPTER_KIND = "Container"
TIER_KIND = "Tier"
APPLICATION_KIND = "BusinessService"
ENTERPRISE_KIND = "Enterprise"
VM_KIND = "VirtualMachine"
NAMESPACE_KIND = "K8S-Namespace"

# The stats read from other objects. The VM KPI is a vCommunity metric, the namespace Performance is Kubernetes'.
VM_KPI_STAT = "vCommunity|VM Guest OS KPI"
NAMESPACE_STAT = "Performance|Performance"

# The object type each metric is published on, and its label: defined in definition.py, with the unit of each.
DEFINED_ON = (
    (TIER_KIND, "Tier", TIER_METRIC),
    (APPLICATION_KIND, "Business Application", APPLICATION_METRIC),
    (ENTERPRISE_KIND, "Enterprise", ENTERPRISE_METRIC),
)


def tier_performance(vm_kpis: List[float]) -> Optional[float]:
    """The average of the VM KPIs of a Tier's VMs. None when no VM has a value."""
    if not vm_kpis:
        return None
    return round(sum(vm_kpis) / len(vm_kpis), 2)


def application_performance(namespace_values: List[float], tier_values: List[float]) -> Optional[float]:
    """The higher of the namespace values, and the lowest tier value. A part with no value is left out.
    None when neither part has a value."""
    candidates = list(namespace_values)
    if tier_values:
        candidates.append(min(tier_values))
    if not candidates:
        return None
    return round(max(candidates), 2)


def enterprise_performance(application_values: List[float]) -> Optional[float]:
    """The average of the Business Applications that have a value. None when none has one."""
    if not application_values:
        return None
    return round(sum(application_values) / len(application_values), 2)


def _objects_of_kind(suite_api_client: SuiteApiClient, resource_kind: str) -> Dict[str, Object]:
    """{VCF Operations id: SDK object} of every Container object of one kind, under every adapter instance.

    The SDK's query_for_resources() drops the ids, which the relationship reads need, so the query is made here.
    """
    query = {"adapterKind": [CONTAINER_ADAPTER_KIND], "resourceKind": [resource_kind]}
    response = suite_api_client.paged_post(RESOURCES_QUERY_PATH, "resourceList", json=query)
    return {item["identifier"]: key_to_object(item["resourceKey"]) for item in response.get("resourceList", [])}


def _ids_of_kind(related: List[Related], kind: str) -> List[str]:
    return [item.id for item in related if item.kind == kind]


def collect_business_applications(suite_api_client: SuiteApiClient, result: CollectResult) -> None:
    """Publishes the Tier, Business Application and Enterprise performance. A failure is logged and stops this
    collection: the values already published stay, the later ones are not published, and the other collections go on."""
    try:
        tiers = _objects_of_kind(suite_api_client, TIER_KIND)
        applications = _objects_of_kind(suite_api_client, APPLICATION_KIND)
        enterprises = _objects_of_kind(suite_api_client, ENTERPRISE_KIND)

        # Tier: the VMs of each Tier, and the VM KPI of those VMs.
        tier_vms = {tier_id: _ids_of_kind(read_related(suite_api_client, tier_id, "CHILD"), VM_KIND) for tier_id in tiers}
        vm_ids = sorted({vm for vms in tier_vms.values() for vm in vms})
        vm_kpis = read_latest_stats(suite_api_client, vm_ids, [VM_KPI_STAT]) if vm_ids else {}
        tier_values = {}
        for tier_id, vms in tier_vms.items():
            kpis = [vm_kpis[vm][VM_KPI_STAT] for vm in vms if VM_KPI_STAT in vm_kpis.get(vm, {})]
            value = tier_performance(kpis)
            if value is not None:
                tiers[tier_id].with_metric(f"vCommunity|{GROUP}|{TIER_METRIC}", value)
                result.add_object(tiers[tier_id])
                tier_values[tier_id] = value

        # Business Application: its Tiers, and the K8S Namespaces within two levels of it.
        application_tiers = {}
        application_namespaces = {}
        for application_id in applications:
            children = read_related(suite_api_client, application_id, "CHILD")
            application_tiers[application_id] = _ids_of_kind(children, TIER_KIND)
            namespaces = _ids_of_kind(children, NAMESPACE_KIND)
            # Level 2 below the Business Application, through the children that are not Tiers. A Tier's own children
            # are its VMs, which are not namespaces.
            for child in children:
                if child.kind != TIER_KIND:
                    namespaces += _ids_of_kind(read_related(suite_api_client, child.id, "CHILD"), NAMESPACE_KIND)
            application_namespaces[application_id] = sorted(set(namespaces))
        namespace_ids = sorted({ns for ids in application_namespaces.values() for ns in ids})
        namespace_stats = read_latest_stats(suite_api_client, namespace_ids, [NAMESPACE_STAT]) if namespace_ids else {}

        application_values = {}
        for application_id, application in applications.items():
            namespace_values = [
                namespace_stats[ns][NAMESPACE_STAT] for ns in application_namespaces[application_id]
                if NAMESPACE_STAT in namespace_stats.get(ns, {})
            ]
            tier_list = [tier_values[t] for t in application_tiers[application_id] if t in tier_values]
            value = application_performance(namespace_values, tier_list)
            if value is not None:
                application.with_metric(f"vCommunity|{GROUP}|{APPLICATION_METRIC}", value)
                result.add_object(application)
                application_values[application_id] = value

        # Enterprise: the Business Applications of each Enterprise.
        for enterprise_id, enterprise in enterprises.items():
            children = read_related(suite_api_client, enterprise_id, "CHILD")
            values = [application_values[a] for a in _ids_of_kind(children, APPLICATION_KIND) if a in application_values]
            value = enterprise_performance(values)
            if value is not None:
                enterprise.with_metric(f"vCommunity|{GROUP}|{ENTERPRISE_METRIC}", value)
                result.add_object(enterprise)
    except Exception as e:
        # A failure must not stop the rest of the collection. The Business Application and Enterprise values need the whole tree,
        # so none is published after the failure.
        logger.warning(f"Business Application performance failed - {repr(e)}")
