#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Collection health: the warnings and errors of one cycle, counted and published on the vCenter object.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from utils import collection_health as ch


class FakeKey:
    def __init__(self, adapter_kind, object_kind):
        self.adapter_kind = adapter_kind
        self.object_kind = object_kind


class FakeObject:
    def __init__(self, adapter_kind, object_kind):
        self._key = FakeKey(adapter_kind, object_kind)
        self.metrics = {}
        self.properties = {}

    def get_key(self):
        return self._key

    def with_metric(self, key, value):
        self.metrics[key] = value

    def with_property(self, key, value):
        self.properties[key] = value


def test_only_warnings_and_errors_are_counted():
    log = logging.getLogger("collection-health-test")
    counter = ch.start()
    try:
        log.info("routine message")
        log.warning("Failed to retrieve something for : esx01 - reason")
        log.error("Skipping Cluster data collection on c1 due to error: reason")
    finally:
        ch.stop(counter)
    assert counter.count == 2


def test_first_warning_is_kept_and_cut_to_the_limit():
    log = logging.getLogger("collection-health-test")
    counter = ch.start()
    try:
        log.warning("Failed to retrieve A " + "x" * 400)
        log.warning("Failed to retrieve B")
    finally:
        ch.stop(counter)
    assert counter.first.startswith("Failed to retrieve A")
    assert len(counter.first) == ch.MAX_TEXT


def test_handler_is_removed_after_the_cycle():
    counter = ch.start()
    ch.stop(counter)
    logging.getLogger("collection-health-test").warning("after the cycle")
    assert counter.count == 0


def test_publish_sets_the_count_and_first_warning_on_the_vcenter_object_only():
    counter = ch.CycleCounter()
    counter.count = 3
    counter.first = "Failed to retrieve X"
    vcenter = FakeObject("VMWARE", "VMwareAdapter Instance")
    host = FakeObject("VMWARE", "HostSystem")
    ch.publish([vcenter, host], counter)
    assert vcenter.metrics == {ch.METRIC_KEY: 3}
    assert vcenter.properties == {ch.PROPERTY_KEY: "Failed to retrieve X"}
    assert host.metrics == {} and host.properties == {}


def test_a_clean_cycle_publishes_zero_and_none():
    vcenter = FakeObject("VMWARE", "VMwareAdapter Instance")
    ch.publish([vcenter], ch.CycleCounter())
    assert vcenter.metrics == {ch.METRIC_KEY: 0}
    assert vcenter.properties == {ch.PROPERTY_KEY: ch.NONE_TEXT}


def test_keys_match_the_alert_definition():
    # The alert in content/alertdefs/Collection Warnings.xml reads this exact metric key.
    assert ch.METRIC_KEY == "vCommunity|Collection Health|Warnings in Last Cycle"
    assert ch.PROPERTY_KEY == "vCommunity|Collection Health|First Warning"
