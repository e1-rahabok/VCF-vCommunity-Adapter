#  Copyright 2026 VCF Operations vCommunity Management Pack
"""VMware Tools on the vSphere World object: how many VMs have no Tools, and how many have Tools down.

    Number of VM without Tools    VMs whose Tools are not installed
    Number of VMware Tools down   VMs that are powered on, have Tools installed, and Tools are not running

Read from the VM properties that the vCenter adapter of VCF Operations stores, for every VM of every vCenter.

Why the power state is needed for "down": a property keeps its last value. A powered-off VM keeps the Tools status it
had when it was last on, which is "not running", so it would be counted as down. A VM that is powered off cannot
have Tools running, and is not a Tools problem. A VM without Tools is counted whatever its power state, because its
Tools are not installed.

A VM with no stored Tools value, such as a template, is left out of both counts.
"""
import logging
from typing import Dict, Iterable, Tuple
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from utils.ops_stats import query_resources, read_latest_properties

logger = logging.getLogger(__name__)

WITHOUT_METRIC = "Number of VM without Tools"
DOWN_METRIC = "Number of VMware Tools down"

# The VCF Operations properties, and the values they hold.
RUNNING_KEY = "summary|guest|toolsRunningStatus"
VERSION_KEY = "summary|guest|toolsVersionStatus2"
POWER_KEY = "summary|runtime|powerState"
NOT_INSTALLED = "Guest Tools Not Installed"
NOT_RUNNING = "Guest Tools Not Running"
POWERED_ON = "Powered On"


def tools_counts(rows: Iterable[Dict[str, str]]) -> Tuple[int, int]:
    """(VMs without Tools, VMs with Tools down), from one row of properties per VM. A missing value is not counted."""
    without = down = 0
    for row in rows:
        version = row.get(VERSION_KEY)
        if version == NOT_INSTALLED:
            without += 1
        elif version and row.get(RUNNING_KEY) == NOT_RUNNING and row.get(POWER_KEY) == POWERED_ON:
            down += 1
    return without, down


def collect_vm_tools_counts(world_obj: Object, suite_api_client: SuiteApiClient) -> None:
    """Publishes the two Tools counts on the vSphere World object."""
    try:
        vms = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "VirtualMachine", None)
        values = read_latest_properties(suite_api_client, [vm.id for vm in vms],
                                        [RUNNING_KEY, VERSION_KEY, POWER_KEY])
        without, down = tools_counts(values.values())
        world_obj.with_metric(f"vCommunity|{WITHOUT_METRIC}", without)
        world_obj.with_metric(f"vCommunity|{DOWN_METRIC}", down)
    except Exception as e:
        # A failure here must not stop the rest of the collection.
        logger.warning(f"Failed to publish the VMware Tools counts on vSphere World - {repr(e)}")
