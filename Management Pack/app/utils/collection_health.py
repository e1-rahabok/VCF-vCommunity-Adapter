#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Collection health: how many warnings and errors the last collection cycle wrote, and the first of them.

A warning in one object or one collector is a logged line only, and the rest of the cycle is published. So a
failure that hides a value would otherwise be silent in VCF Operations. This module counts those warnings during a
cycle and publishes the count on the vCenter object. One alert, "vCommunity Collection Warnings", fires when the count
is above zero (content/alertdefs/Collection Warnings.xml). The alert names the search keywords for the log, and the
property shows the first warning, so the cause can be found without opening every log line.

The count covers every warning and error the adapter logs during the cycle. The first message is kept, cut to
MAX_TEXT characters.
"""
import logging
from typing import Iterable, Optional
from constants.main import VCENTER_ADAPTER_KIND

GROUP = "Collection Health"
WARNINGS_METRIC = "Warnings in Last Cycle"
FIRST_WARNING_PROPERTY = "First Warning"
METRIC_KEY = f"vCommunity|{GROUP}|{WARNINGS_METRIC}"
PROPERTY_KEY = f"vCommunity|{GROUP}|{FIRST_WARNING_PROPERTY}"
VCENTER_OBJECT_KIND = "VMwareAdapter Instance"
NONE_TEXT = "None in the last cycle"
MAX_TEXT = 250


class CycleCounter(logging.Handler):
    """Counts the WARNING and ERROR records of one collection cycle, and keeps the first message."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.count = 0
        self.first: Optional[str] = None

    def emit(self, record: logging.LogRecord) -> None:
        self.count += 1
        if self.first is None:
            self.first = record.getMessage()[:MAX_TEXT]


def start() -> CycleCounter:
    """Starts counting the warnings of this cycle. Call stop() with the result when the cycle ends."""
    counter = CycleCounter()
    logging.getLogger().addHandler(counter)
    return counter


def stop(counter: CycleCounter) -> None:
    logging.getLogger().removeHandler(counter)


def publish(objects: Iterable, counter: CycleCounter) -> None:
    """Publishes the count and the first warning on the vCenter object of this cycle. Other objects are left alone."""
    for obj in objects:
        key = obj.get_key()
        if key.adapter_kind != VCENTER_ADAPTER_KIND or key.object_kind != VCENTER_OBJECT_KIND:
            continue
        obj.with_metric(METRIC_KEY, counter.count)
        obj.with_property(PROPERTY_KEY, counter.first or NONE_TEXT)
