#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Probe: can this pack publish a metric on a Tier object, which belongs to the Container adapter?

A temporary check for the Business Application Tier Performance super metric. Every Tier object in VCF Operations gets
one metric, Probe Value, with the value PROBE_VALUE. If the value shows on the Tier objects, the platform accepts a
metric from this pack on an object of another adapter kind. If it does not show, the log says how many Tier objects
were found. Remove this module once the answer is known.
"""
import logging
from aria.ops.result import CollectResult
from aria.ops.suite_api_client import SuiteApiClient

logger = logging.getLogger(__name__)

TIER_ADAPTER_KIND = "Container"
TIER_KIND = "Tier"
GROUP = "Tier Probe"
PROBE_METRIC = "Probe Value"
PROBE_KEY = f"vCommunity|{GROUP}|{PROBE_METRIC}"
PROBE_VALUE = 42


def collect_tier_probe(suite_api_client: SuiteApiClient, result: CollectResult) -> None:
    try:
        tiers = suite_api_client.query_for_resources(
            {"adapterKind": [TIER_ADAPTER_KIND], "resourceKind": [TIER_KIND]}
        )
        logger.info(f"Tier probe: {len(tiers)} Tier objects found in VCF Operations")
        for tier in tiers:
            tier.with_metric(PROBE_KEY, PROBE_VALUE)
            result.add_object(tier)
    except Exception as e:
        # A failure of the probe must not stop the rest of the collection.
        logger.warning(f"Tier probe failed - {repr(e)}")
