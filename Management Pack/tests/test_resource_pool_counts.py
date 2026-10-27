#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Number of Resource Pools and Cascading Resource Pools, from the parents of each pool.

The live tree on the lab (cluster vcf-m02-cl01) gives 9 and 8, the values of the former super metrics.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.cluster import resource_pool_counts as rpc
from metrics.cluster.resource_pool_counts import Parent

CLUSTER = Parent("ClusterComputeResource", "cluster-1")


def lab_tree():
    """The lab tree: Namespaces under the cluster, seven pools under Namespaces, one more under prod01."""
    namespace_pools = ["prod01", "prod02", "svc-argocd", "svc-cci", "svc-auto-attach", "svc-velero", "svc-tkg"]
    parents = {"Namespaces": [CLUSTER]}
    for pool in namespace_pools:
        parents[pool] = [Parent("ResourcePool", "Namespaces"), Parent("NamespaceV2", f"ns-{pool}")]
    parents["vks-small01"] = [Parent("ResourcePool", "prod01"), Parent("GuestCluster", "gc-1")]
    return parents


def test_levels_of_the_lab_tree():
    levels = rpc.levels(lab_tree())
    assert levels["Namespaces"] == (1, "cluster-1")
    assert levels["prod01"] == (2, "cluster-1")
    assert levels["vks-small01"] == (3, "cluster-1")


def test_lab_tree_gives_the_values_of_the_former_super_metrics():
    counts = rpc.counts_by_cluster(rpc.levels(lab_tree()))
    assert counts == {"cluster-1": (9, 8)}


def test_pools_deeper_than_the_limits_are_not_counted():
    parents = lab_tree()
    # Level 4 and level 6 under vks-small01 and below.
    parents["deep-4"] = [Parent("ResourcePool", "vks-small01")]
    parents["deep-5"] = [Parent("ResourcePool", "deep-4")]
    parents["deep-6"] = [Parent("ResourcePool", "deep-5")]
    count, cascade = rpc.counts_by_cluster(rpc.levels(parents))["cluster-1"]
    assert count == 9                 # levels 1 to 3 only: deep-4 is not in the count
    assert cascade == 8 + 2           # levels 2 to 5: deep-4 and deep-5, not deep-6


def test_a_pool_with_no_path_to_a_cluster_has_no_level():
    parents = lab_tree()
    parents["orphan"] = []
    levels = rpc.levels(parents)
    assert levels["orphan"] == (None, None)
    assert rpc.counts_by_cluster(levels)["cluster-1"] == (9, 8)


def test_a_cycle_in_the_data_has_no_level():
    parents = {"a": [Parent("ResourcePool", "b")], "b": [Parent("ResourcePool", "a")]}
    assert rpc.levels(parents) == {"a": (None, None), "b": (None, None)}


def test_two_clusters_are_counted_separately():
    parents = {"p1": [Parent("ClusterComputeResource", "c1")], "p2": [Parent("ClusterComputeResource", "c2")],
               "p3": [Parent("ResourcePool", "p2")]}
    assert rpc.counts_by_cluster(rpc.levels(parents)) == {"c1": (1, 0), "c2": (2, 1)}


def test_link_parsing_takes_the_id_from_the_self_link():
    item = {"links": [{"rel": "SELF", "href": "/suite-api/api/resources/abc-123/relationships?page=0"}]}
    assert rpc._id_of(item) == "abc-123"
    assert rpc._id_of({"links": []}) is None
