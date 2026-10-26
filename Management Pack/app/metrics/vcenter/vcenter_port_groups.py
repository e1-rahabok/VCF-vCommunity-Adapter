#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Number of Port Groups on one vCenter: the port groups of every Datacenter, distributed and standard.

A port group's namespace is its Datacenter. Within one Datacenter, a name counts once, whether it is a distributed
port group or a standard one (defined on each host). The same name in two Datacenters of one vCenter counts twice.

    Number of Port Groups (vCenter) = sum over its Datacenters of the distinct port group names in each

Read from the vSphere API, because the Datacenter is needed and VCF Operations does not give it for port groups.
Published as a metric on the vCenter object. The vSphere World metric adds up the vCenters, see
metrics/world/port_group_counts.py.

A failed read raises. Nothing is published then, so the metric keeps its last value for the configuration limit
(CONFIGURATION_STALE_AFTER_MINUTES) and no false zero is stored.
"""
import logging
from typing import Any, Dict, Iterable, List
from aria.ops.object import Object
from pyVmomi import vmodl, vim

logger = logging.getLogger(__name__)

METRIC = "Number of Port Groups"
METRIC_KEY = f"vCommunity|{METRIC}"


def count_port_groups(names_by_datacenter: Dict[str, Iterable[Iterable[str]]]) -> int:
    """The number of port groups of a vCenter. names_by_datacenter maps each Datacenter to the lists of port group
    names it has: one list per host (standard port groups), and one for its distributed port groups. Within a
    Datacenter, a name counts once."""
    return sum(len({name for names in lists for name in names}) for lists in names_by_datacenter.values())


def read_port_group_names(content: Any) -> Dict[str, List[List[str]]]:
    """{Datacenter id: [standard port group names of each host] + [distributed port group names]}, read from the
    vSphere API. Raises on any failure."""
    names: Dict[str, List[List[str]]] = {}
    datacenters = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datacenter], True)
    try:
        for datacenter in datacenters.view:
            host_lists = _host_port_group_names(content, datacenter.hostFolder)
            distributed = _names_under(content, datacenter.networkFolder, vim.dvs.DistributedVirtualPortgroup)
            names[datacenter._moId] = host_lists + [distributed]
    finally:
        datacenters.Destroy()
    return names


def _host_port_group_names(content: Any, container: Any) -> List[List[str]]:
    """The standard port group names of each host under one container, such as a Datacenter's host folder."""
    lists: List[List[str]] = []
    for names in _collect_properties(content, container, vim.HostSystem, "config.network.portgroup"):
        lists.append([group.spec.name for group in (names or [])])
    return lists


def _names_under(content: Any, container: Any, object_type: Any) -> List[str]:
    """The names of the objects of one type under a container, such as the distributed port groups of a Datacenter."""
    return list(_collect_properties(content, container, object_type, "name"))


def _collect_properties(content: Any, container: Any, object_type: Any, path: str) -> List[Any]:
    """The value of one property of every object of one type under a container. Raises on failure."""
    view = content.viewManager.CreateContainerView(container, [object_type], True)
    try:
        spec = vmodl.query.PropertyCollector.FilterSpec(
            objectSet=[vmodl.query.PropertyCollector.ObjectSpec(
                obj=view,
                skip=False,
                selectSet=[vmodl.query.PropertyCollector.TraversalSpec(
                    name="traverseEntities", path="view", skip=False, type=vim.view.ContainerView)],
            )],
            propSet=[vmodl.query.PropertyCollector.PropertySpec(type=object_type, pathSet=[path], all=False)],
        )
        options = vmodl.query.PropertyCollector.RetrieveOptions(maxObjects=100)
        result = content.propertyCollector.RetrievePropertiesEx([spec], options)
        values: List[Any] = []
        while result:
            for obj in result.objects or []:
                for prop in obj.propSet:
                    if prop.name == path:
                        values.append(prop.val)
            if not result.token:
                break
            result = content.propertyCollector.ContinueRetrievePropertiesEx(result.token)
        return values
    finally:
        view.Destroy()


def collect_port_group_count(vcenter_obj: Object, content: Any) -> None:
    """Publishes Number of Port Groups on this vCenter. On a failed read, nothing is published."""
    try:
        count = count_port_groups(read_port_group_names(content))
    except Exception as e:
        logger.warning(f"Failed to count the port groups of this vCenter, so {METRIC} is not updated - {repr(e)}")
        return
    vcenter_obj.with_metric(METRIC_KEY, count)
