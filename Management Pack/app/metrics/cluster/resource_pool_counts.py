#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Number of Resource Pools and Cascading Resource Pools, per cluster. Read from VCF Operations, not from vCenter.

A resource pool's level is its distance from the cluster: a pool directly under the cluster is level 1, a pool under a
level 1 pool is level 2, and so on. The two metrics are:

    Number of Resource Pools     pools at level 1 to 3
    Cascading Resource Pools     pools at level 2 to 5 (a cascade: a pool under another pool)

These are the same counts as the former super metrics of the same names, which counted depth 1 to 3 and depth 1 to 5
(depth 5 minus depth 1 for the cascade). A pool deeper than 5 is not counted in either, as before.

The parents of each pool come from its PARENT relationship in VCF Operations, one request per pool. A pool whose
parents cannot be read is left out, and a pool whose parent chain never reaches a cluster has no cluster.
"""
import logging
from typing import Dict, Iterable, List, NamedTuple, Optional, Tuple
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from utils.ops_stats import query_resources

logger = logging.getLogger(__name__)

GROUP = "Resource Pools"
COUNT_METRIC = "Number of Resource Pools"
CASCADING_METRIC = "Cascading Resource Pools"
COUNT_MAX_LEVEL = 3
CASCADE_MIN_LEVEL = 2
CASCADE_MAX_LEVEL = 5

CLUSTER_KIND = "ClusterComputeResource"
POOL_KIND = "ResourcePool"


class Parent(NamedTuple):
    kind: str       # resource kind key, such as ResourcePool or ClusterComputeResource
    id: str         # VCF Operations resource id


def levels(parents_by_pool: Dict[str, List[Parent]]) -> Dict[str, Tuple[Optional[int], Optional[str]]]:
    """{pool id: (level, cluster id)} from each pool's parents. A pool with no path to a cluster has (None, None)."""
    result: Dict[str, Tuple[Optional[int], Optional[str]]] = {}

    def resolve(pool: str, seen: frozenset) -> Tuple[Optional[int], Optional[str]]:
        if pool in result:
            return result[pool]
        if pool in seen:             # a cycle in the data: no level
            return (None, None)
        answer: Tuple[Optional[int], Optional[str]] = (None, None)
        for parent in parents_by_pool.get(pool, []):
            if parent.kind == CLUSTER_KIND:
                answer = (1, parent.id)
                break
            if parent.kind == POOL_KIND and parent.id in parents_by_pool:
                level, cluster = resolve(parent.id, seen | {pool})
                if level is not None:
                    answer = (level + 1, cluster)
                    break
        result[pool] = answer
        return answer

    for pool in parents_by_pool:
        resolve(pool, frozenset())
    return result


def counts_by_cluster(pool_levels: Dict[str, Tuple[Optional[int], Optional[str]]]) -> Dict[str, Tuple[int, int]]:
    """{cluster id: (Number of Resource Pools, Cascading Resource Pools)} for the clusters that have a pool."""
    counts: Dict[str, List[int]] = {}
    for level, cluster in pool_levels.values():
        if level is None or cluster is None:
            continue
        count, cascade = counts.setdefault(cluster, [0, 0])
        if level <= COUNT_MAX_LEVEL:
            count += 1
        if CASCADE_MIN_LEVEL <= level <= CASCADE_MAX_LEVEL:
            cascade += 1
        counts[cluster] = [count, cascade]
    return {cluster: (count, cascade) for cluster, (count, cascade) in counts.items()}


def _id_of(item: Dict) -> Optional[str]:
    """The VCF Operations id of a relationship item: the id in its SELF link."""
    for link in item.get("links", []):
        if link.get("rel") == "SELF" and "/resources/" in link.get("href", ""):
            return link["href"].rsplit("/resources/", 1)[1].split("/")[0].split("?")[0]
    return None


def read_parents(suite_api_client: SuiteApiClient, pool_ids: Iterable[str]) -> Dict[str, List[Parent]]:
    """{pool id: its parents}, from one PARENT relationship request per pool. Raises if any request fails: a pool
    whose parents are missing would be left out of its cluster's count without a sign, which is a wrong number."""
    parents: Dict[str, List[Parent]] = {}
    for pool_id in pool_ids:
        response = suite_api_client.get(url=f"api/resources/{pool_id}/relationships?relationshipType=PARENT")
        if response.status_code != 200:
            raise RuntimeError(f"Resource pool parents of {pool_id} could not be read: HTTP {response.status_code}")
        parents[pool_id] = [
            Parent(item["resourceKey"]["resourceKindKey"], _id_of(item))
            for item in response.json().get("resourceList", [])
            if _id_of(item)
        ]
    return parents


def read_counts(suite_api_client: SuiteApiClient, adapter_instance_id: str) -> Dict[str, Tuple[int, int]]:
    """{cluster id: (Number of Resource Pools, Cascading Resource Pools)} for the pools of one vCenter. Raises if the
    parents of any pool cannot be read: no count is published then, rather than a wrong one."""
    pools = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, POOL_KIND, adapter_instance_id)
    parents = read_parents(suite_api_client, [pool.id for pool in pools])
    return counts_by_cluster(levels(parents))


def publish(cluster_obj, counts: Optional[Tuple[int, int]]) -> None:
    """Publishes both counts on a cluster. Nothing when the cluster has no pools read this cycle."""
    if counts is None:
        return
    count, cascade = counts
    cluster_obj.with_metric(f"vCommunity|{GROUP}|{COUNT_METRIC}", count)
    cluster_obj.with_metric(f"vCommunity|{GROUP}|{CASCADING_METRIC}", cascade)
