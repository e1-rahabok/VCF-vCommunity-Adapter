#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Reads what VCF Operations already holds: resources, their stats and their properties.

The vCenter adapter of VCF Operations has already collected all of it. The KPIs read it back through the
Suite API, so nothing is collected twice.
"""
import logging
import time
from typing import Dict, List, NamedTuple, Optional
from aria.ops.suite_api_client import SuiteApiClient

logger = logging.getLogger(__name__)

# Suite API endpoints. Each takes many resources in one request.
RESOURCES_QUERY_PATH = "/api/resources/query"
LATEST_STATS_PATH = "api/resources/stats/latest/query"
STATS_QUERY_PATH = "api/resources/stats/query"
LATEST_PROPERTIES_PATH = "api/resources/properties/latest/query"

# One request asks for at most this many resources. A VM KPI needs stats for every VM,
# and a single request for thousands of VMs is slow and can time out.
RESOURCES_PER_REQUEST = 1000

# VCF Operations stores one sample per 5-minute collection cycle.
COLLECTION_CYCLE_MINUTES = 5

# A latest stat older than this is no data. The latest query returns the last stored value however old it
# is: an object that stopped reporting (a host that is down or disconnected, a VM that is powered off) keeps
# its last value as "latest". Using it would publish a value that no longer reflects reality, so the metric
# is left blank instead. Two cycles, so that one late collection does not blank everything.
# Properties are not filtered: they are stored only when they change, so their last known value is current.
STALE_AFTER_MINUTES = 2 * COLLECTION_CYCLE_MINUTES

# The one exception to STALE_AFTER_MINUTES: a metric based on settings, such as the number of port groups, changes
# rarely, so its last known value is kept for longer. Only metrics that name this limit explicitly use it. The
# reasons and the list are in docs/reference/metrics/README.md#no-stale-values.
CONFIGURATION_STALE_AFTER_MINUTES = 15


def read_latest_stats(
    suite_api_client: SuiteApiClient, resource_ids: List[str], stat_keys: List[str],
    max_age_minutes: float = STALE_AFTER_MINUTES,
) -> Dict[str, Dict[str, float]]:
    """Returns {resource id: {stat key: latest value}}. Stats with no data, or older than max_age_minutes
    (STALE_AFTER_MINUTES by default), are absent."""
    query = {"resourceId": resource_ids, "statKey": stat_keys}
    samples_by_resource = _query_stats(suite_api_client, LATEST_STATS_PATH, query, max_age_minutes=max_age_minutes)
    return {
        resource_id: {stat_key: samples[-1] for stat_key, samples in samples_by_key.items()}
        for resource_id, samples_by_key in samples_by_resource.items()
    }


def read_latest_timestamps(
    suite_api_client: SuiteApiClient, resource_ids: List[str], stat_keys: List[str]
) -> Optional[Dict[str, Dict[str, float]]]:
    """Returns {resource id: {stat key: time of its latest sample, in epoch ms}}, however old the sample is.

    A stat that was never published is absent. None when a request failed: the caller cannot tell "never
    published" from "not read", so it must not act on a partial answer.
    """
    timestamps = {}
    requested_keys = set(stat_keys)
    for start in range(0, len(resource_ids), RESOURCES_PER_REQUEST):
        batch = resource_ids[start:start + RESOURCES_PER_REQUEST]
        response = suite_api_client.post(LATEST_STATS_PATH, json={"resourceId": batch, "statKey": stat_keys})
        if response.status_code != 200:
            logger.warning(f"Stats query {LATEST_STATS_PATH} failed with HTTP {response.status_code}")
            return None
        for resource in response.json().get("values", []):
            stat_list = resource.get("stat-list") or resource.get("stats") or {}
            by_key = timestamps.setdefault(resource.get("resourceId"), {})
            for stat in stat_list.get("stat", []):
                stat_key = stat.get("statKey", {}).get("key")
                if stat_key in requested_keys and stat.get("timestamps"):
                    by_key[stat_key] = float(max(stat["timestamps"]))
    return timestamps


def read_latest_instance_stats(
    suite_api_client: SuiteApiClient, resource_ids: List[str], stat_keys: List[str]
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Returns {resource id: {stat key: {instance: latest value}}}, one value per instance.

    Asked for "net|speed", VCF Operations also returns one stat per instance, such as "net:vmnic0|speed"
    for NIC vmnic0. Those are kept here, by instance name. The stat without an instance is left out.
    Values older than STALE_AFTER_MINUTES are absent.
    """
    query = {"resourceId": resource_ids, "statKey": stat_keys}
    samples_by_resource = _query_stats(suite_api_client, LATEST_STATS_PATH, query, keep_instances=True,
                                       max_age_minutes=STALE_AFTER_MINUTES)
    values = {}
    for resource_id, samples_by_key in samples_by_resource.items():
        for full_key, samples in samples_by_key.items():
            instance, stat_key = split_instance(full_key)
            if instance is not None:
                values.setdefault(resource_id, {}).setdefault(stat_key, {})[instance] = samples[-1]
    return values


def read_stat_history(
    suite_api_client: SuiteApiClient, resource_ids: List[str], stat_keys: List[str],
    begin_ms: int, end_ms: int, resources_per_request: int, failed: List[str],
) -> Dict[str, Dict[str, List[float]]]:
    """Returns {resource id: {stat key: [5-minute samples between begin_ms and end_ms, oldest first]}}.

    A day of history is 288 samples per stat, so a request holds fewer resources than the latest queries:
    resources_per_request. The ids of the resources whose request failed are added to failed, so the caller
    can tell "no data" from "not read".
    """
    query = {
        "resourceId": resource_ids,
        "statKey": stat_keys,
        "begin": begin_ms,
        "end": end_ms,
        "rollUpType": "AVG",
        "intervalType": "MINUTES",
        "intervalQuantifier": COLLECTION_CYCLE_MINUTES,
    }
    return _query_stats(suite_api_client, STATS_QUERY_PATH, query,
                        resources_per_request=resources_per_request, failed=failed)


def split_instance(stat_key: str):
    """"net:vmnic0|speed" -> ("vmnic0", "net|speed"). A key without an instance -> (None, the key)."""
    group, separator, rest = stat_key.partition("|")
    if ":" not in group or not separator:
        return None, stat_key
    name, _, instance = group.partition(":")
    return instance, f"{name}|{rest}"


def _query_stats(
    suite_api_client: SuiteApiClient, path: str, query: dict, keep_instances: bool = False,
    resources_per_request: Optional[int] = None, failed: Optional[List[str]] = None,
    max_age_minutes: Optional[float] = None,
) -> Dict[str, Dict[str, List[float]]]:
    """Returns {resource id: {stat key: [samples, oldest first]}}. Resources of a failed request are absent,
    and added to failed when it is given. resources_per_request defaults to RESOURCES_PER_REQUEST.

    max_age_minutes: samples older than this are dropped, and a stat left with none is absent.
    """
    resources_per_request = resources_per_request or RESOURCES_PER_REQUEST
    oldest_ms = None if max_age_minutes is None else (time.time() - max_age_minutes * 60) * 1000
    resource_ids = query["resourceId"]
    requested_keys = set(query["statKey"])
    samples_by_resource = {}

    for start in range(0, len(resource_ids), resources_per_request):
        batch = resource_ids[start:start + resources_per_request]
        response = suite_api_client.post(path, json={**query, "resourceId": batch})
        if response.status_code != 200:
            logger.warning(f"Stats query {path} failed with HTTP {response.status_code}")
            if failed is not None:
                failed.extend(batch)
            continue

        for resource in response.json().get("values", []):
            # The JSON key is "stat-list" on the wire, but the API reference calls it "stats".
            stat_list = resource.get("stat-list") or resource.get("stats") or {}
            samples_by_key = samples_by_resource.setdefault(resource.get("resourceId"), {})
            for stat in stat_list.get("stat", []):
                stat_key = stat.get("statKey", {}).get("key")
                samples = stat.get("data") or []
                timestamps = stat.get("timestamps") or []
                if oldest_ms is not None and len(timestamps) == len(samples):
                    samples = [sample for sample, ts in zip(samples, timestamps) if ts >= oldest_ms]
                # VCF Operations also returns every instance of a requested stat, such as
                # "cpu:26|utilization_average" for CPU thread 26. Only the requested keys are kept,
                # and their instances when keep_instances is set.
                requested = stat_key in requested_keys or (keep_instances and split_instance(stat_key or "")[1] in requested_keys)
                if requested and samples:
                    samples_by_key[stat_key] = [float(sample) for sample in samples]
    return samples_by_resource


# ---------------------------------------------------------------------------
# Resources and properties.
# ---------------------------------------------------------------------------

class OpsResource(NamedTuple):
    """One VCF Operations resource, such as an ESXi host or a VM."""
    id: str             # VCF Operations resource id, which the stats and properties API need
    name: str           # the name shown in vCenter
    moid: str           # vCenter MoRef id (identifier VMEntityObjectID), to match the SDK objects


def query_resources(
    suite_api_client: SuiteApiClient, adapter_kind: str, resource_kind: str, adapter_instance_id: Optional[str]
) -> List[OpsResource]:
    """All resources of one kind under one adapter instance, with their VCF Operations ids.
    With adapter_instance_id None: under every adapter instance, for example the clusters of all vCenters.

    The SDK's query_for_resources() drops the resource id, so the query is made here directly.
    """
    query = {"adapterKind": [adapter_kind], "resourceKind": [resource_kind]}
    if adapter_instance_id is not None:
        query["adapterInstanceId"] = [adapter_instance_id]
    response = suite_api_client.paged_post(RESOURCES_QUERY_PATH, "resourceList", json=query)
    resources = []
    for resource in response.get("resourceList", []):
        key = resource.get("resourceKey", {})
        moid = next((identifier.get("value") for identifier in key.get("resourceIdentifiers", [])
                     if identifier.get("identifierType", {}).get("name") == "VMEntityObjectID"), None)
        resources.append(OpsResource(resource.get("identifier"), key.get("name"), moid))
    return resources


def read_latest_properties(
    suite_api_client: SuiteApiClient, resource_ids: List[str], property_keys: List[str]
) -> Dict[str, Dict[str, str]]:
    """Returns {resource id: {property key: latest value}}. Properties with no value are absent.

    Values are returned as text, as VCF Operations stores most properties. Convert numbers with as_number().
    """
    properties_by_resource = {}
    for start in range(0, len(resource_ids), RESOURCES_PER_REQUEST):
        request = {"resourceIds": resource_ids[start:start + RESOURCES_PER_REQUEST], "propertyKeys": property_keys}
        response = suite_api_client.post(LATEST_PROPERTIES_PATH, json=request)
        if response.status_code != 200:
            logger.warning(f"Properties query failed with HTTP {response.status_code}")
            continue

        for resource in response.json().get("values", []):
            contents = resource.get("property-contents", {}).get("property-content", [])
            properties = properties_by_resource.setdefault(resource.get("resourceId"), {})
            for content in contents:
                # A text property has "values", a number property has "data". Take the latest of either.
                samples = content.get("values") or content.get("data") or []
                if content.get("statKey") and samples:
                    properties[content["statKey"]] = str(samples[-1])
    return properties_by_resource


def as_number(value: Optional[str]) -> Optional[float]:
    """A property value as a number, or None when it is missing or not a number."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
