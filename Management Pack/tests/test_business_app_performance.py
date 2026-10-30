#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Business Application performance: Tier, Business Application and Enterprise, from the VMs, namespaces and
relationships of VCF Operations. The formulas are those of the former super metrics.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from aria.ops.result import CollectResult
from metrics.container import business_app_performance as bap

KEY_TIER = "vCommunity|Business Application|Tier Performance"
KEY_APP = "vCommunity|Business Application|Business Application Performance"
KEY_ENTERPRISE = "vCommunity|Business Application|Business Applications Performance"


class FakeResponse:
    def __init__(self, body, status_code=200):
        self.body = body
        self.status_code = status_code

    def json(self):
        return self.body


class FakeSuiteApi:
    """Container objects by kind, the relationships between them, and the stats of VMs and namespaces.

    objects:       {kind: [(id, name)]}
    children:      {id: [(kind, child id)]}, for the CHILD relationship. Missing ids have no children.
    stats:         {id: {stat key: value}}, read as the latest value, one 5-minute cycle ago at most.
    failing:       ids whose relationship request fails with HTTP 500.
    """

    def __init__(self, objects=None, children=None, stats=None, failing=None):
        self.objects = objects or {}
        self.children = children or {}
        self.stats = stats or {}
        self.failing = failing or set()

    def paged_post(self, path, key, json):
        kind = json["resourceKind"][0]
        return {key: [
            {"identifier": resource_id, "resourceKey": {
                "adapterKindKey": "Container", "resourceKindKey": kind, "name": name, "resourceIdentifiers": []}}
            for resource_id, name in self.objects.get(kind, [])
        ]}

    def get(self, url):
        resource_id = url.split("/")[2]
        if resource_id in self.failing:
            return FakeResponse({}, 500)
        items = [
            {"resourceKey": {"resourceKindKey": kind},
             "links": [{"rel": "SELF", "href": f"/suite-api/api/resources/{child}"}]}
            for kind, child in self.children.get(resource_id, [])
        ]
        return FakeResponse({"resourceList": items})

    def post(self, path, json):
        now_ms = time.time() * 1000
        values = []
        for resource_id in json["resourceId"]:
            stats = [
                {"statKey": {"key": key}, "data": [value], "timestamps": [now_ms]}
                for key, value in self.stats.get(resource_id, {}).items() if key in json["statKey"]
            ]
            values.append({"resourceId": resource_id, "stat-list": {"stat": stats}})
        return FakeResponse({"values": values})


def metric_on(result, name, key):
    for obj in result.objects.values():
        if obj.get_key().name == name:
            values = obj.get_metric_values(key)
            return values[-1] if values else None
    return None


# ---------------------------------------------------------------------------
# The formulas.
# ---------------------------------------------------------------------------

def test_tier_is_the_average_of_its_vm_kpis():
    assert bap.tier_performance([80.0, 60.0]) == 70.0


def test_tier_with_no_vm_kpi_has_no_value():
    assert bap.tier_performance([]) is None


def test_application_is_the_higher_of_namespace_and_lowest_tier():
    assert bap.application_performance([90.0], [70.0, 80.0]) == 90.0
    assert bap.application_performance([50.0], [70.0, 80.0]) == 70.0


def test_application_uses_the_parts_that_have_a_value():
    assert bap.application_performance([], [70.0, 80.0]) == 70.0
    assert bap.application_performance([90.0], []) == 90.0


def test_application_with_no_value_has_no_value():
    assert bap.application_performance([], []) is None


def test_enterprise_is_the_average_of_its_applications():
    assert bap.enterprise_performance([60.0, 80.0]) == 70.0
    assert bap.enterprise_performance([]) is None


# ---------------------------------------------------------------------------
# The collector, over a fake VCF Operations.
# ---------------------------------------------------------------------------

def lab():
    """Two Business Applications under one Enterprise. AI has a namespace; Bank has none.

    LLM: VMs with KPIs 80 and 60, so 70. Web: its only VM has no KPI, so it has no value.
    AI: namespace 90, tiers LLM (70) and Web (no value), so 90.
    Bank: no namespace, tier LLM (70), so 70.
    Enterprise: AI and Bank, so 80.
    """
    fake = FakeSuiteApi(
        objects={
            "Tier": [("llm", "LLM"), ("web", "Web")],
            "BusinessService": [("ai", "AI"), ("bank", "Internet Banking")],
            "Enterprise": [("ent", "Enterprise")],
        },
        children={
            "ai": [("Tier", "llm"), ("Tier", "web"), ("K8S-Namespace", "ns-ai")],
            "bank": [("Tier", "llm")],
            "ent": [("BusinessService", "ai"), ("BusinessService", "bank")],
            "llm": [("VirtualMachine", "vm1"), ("VirtualMachine", "vm2")],
            "web": [("VirtualMachine", "vm3")],
        },
        stats={
            "vm1": {bap.VM_KPI_STAT: 80.0},
            "vm2": {bap.VM_KPI_STAT: 60.0},
            "vm3": {},
            "ns-ai": {bap.NAMESPACE_STAT: 90.0},
        },
    )
    return fake


def test_lab_publishes_tier_application_and_enterprise_values():
    result = CollectResult()
    bap.collect_business_applications(lab(), result)
    assert metric_on(result, "LLM", KEY_TIER) == 70.0
    assert metric_on(result, "AI", KEY_APP) == 90.0
    assert metric_on(result, "Internet Banking", KEY_APP) == 70.0
    assert metric_on(result, "Enterprise", KEY_ENTERPRISE) == 80.0


def test_a_tier_without_vm_kpi_publishes_nothing():
    result = CollectResult()
    bap.collect_business_applications(lab(), result)
    assert metric_on(result, "Web", KEY_TIER) is None
    assert "Web" not in [obj.get_key().name for obj in result.objects.values()]


def test_a_namespace_is_found_within_two_levels():
    fake = FakeSuiteApi(
        objects={"BusinessService": [("ai", "AI")]},
        children={"ai": [("Other", "mid")], "mid": [("K8S-Namespace", "ns-deep")]},
        stats={"ns-deep": {bap.NAMESPACE_STAT: 65.0}},
    )
    result = CollectResult()
    bap.collect_business_applications(fake, result)
    assert metric_on(result, "AI", KEY_APP) == 65.0


def test_a_failed_relationship_read_publishes_no_application_or_enterprise_value():
    fake = lab()
    fake.failing = {"ai"}
    result = CollectResult()
    bap.collect_business_applications(fake, result)
    # The Tier values were complete before the failure, so they stay. The Business Application and the Enterprise
    # need the whole tree, so they are not published rather than published from part of it.
    assert metric_on(result, "LLM", KEY_TIER) == 70.0
    assert metric_on(result, "AI", KEY_APP) is None
    assert metric_on(result, "Enterprise", KEY_ENTERPRISE) is None


def test_no_objects_publishes_nothing():
    result = CollectResult()
    bap.collect_business_applications(FakeSuiteApi(), result)
    assert len(result.objects) == 0
