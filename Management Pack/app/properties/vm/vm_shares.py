#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Share per vCPU and Share per MB of Memory: a VM's CPU and memory shares, normalised by its size.

Shares grow with the size of the VM, so raw shares cannot be compared between VMs. Per vCPU and per MB they can.
Published as properties on every VM, powered on or off. No value when the VM has no vCPU, no memory size or no
shares, instead of a division by zero.

Called from: collectors/vm/collectVMData.py. Description: docs/reference/metrics/vm-shares.md
"""
import logging
from typing import Dict, List, Optional
from aria.ops.definition.units import Unit
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from utils.ops_inventory import VmInfo
from utils.ops_stats import as_number, read_latest_properties, read_latest_stats

logger = logging.getLogger(__name__)

# Where the properties are published: the existing "Configuration" group of the VM, next to the share levels.
GROUP = "Configuration"
CPU_PROPERTY = "Share per vCPU"
MEMORY_PROPERTY = "Share per MB of Memory"

class _CountUnit:
    """TEST (0.6.6 build only): the unit "count", which the SDK does not define.

    The SDK takes a unit from its enum and reads only unit.value.key and unit.value.is_rate, so this object gives it
    those two values. A plain Unit is refused: the SDK reads unit.value, and fails to build the definition.
    """
    value = Unit("count", "count", 1, 1)


COUNT_UNIT = _CountUnit()
# TEST (0.6.6 build only): the same value as a metric, to compare with the property on the same object.
TEST_METRIC = "Share per vCPU (count unit test)"

CPU_SHARES = "config|cpuAllocation|shares|shares"
MEMORY_SHARES = "config|memoryAllocation|shares|shares"
SHARE_KEYS = [CPU_SHARES, MEMORY_SHARES]


def per_unit(shares: Optional[float], units: Optional[float]) -> Optional[float]:
    """shares / units. None when either is missing, or units is 0."""
    if shares is None or not units:
        return None
    return shares / units


def read_vm_shares(suite_api_client: SuiteApiClient, vm_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """{VM id: {share key: shares}}, read in bulk. Read as properties, or as stats when stored as stats."""
    try:
        properties = read_latest_properties(suite_api_client, vm_ids, SHARE_KEYS)
        shares = {
            vm_id: {key: as_number(value) for key, value in values.items() if as_number(value) is not None}
            for vm_id, values in properties.items()
        }
        missing = [vm_id for vm_id in vm_ids if len(shares.get(vm_id, {})) < len(SHARE_KEYS)]
        if missing:
            for vm_id, values in read_latest_stats(suite_api_client, missing, SHARE_KEYS).items():
                shares.setdefault(vm_id, {}).update({key: value for key, value in values.items()
                                                     if key not in shares.get(vm_id, {})})
        return shares
    except Exception as e:
        # Without shares there is no value, but the rest of the VM collection must still run.
        logger.warning(f"Failed to read VM shares, so no Share per vCPU or per MB this cycle - {repr(e)}")
        return {}


def collect_vm_shares(vm_obj: Object, vm_name: str, vm: VmInfo, shares: Dict[str, float]) -> None:
    """Publishes Share per vCPU and Share per MB of Memory. shares is the entry of this VM in read_vm_shares()."""
    try:
        values = {
            CPU_PROPERTY: per_unit(shares.get(CPU_SHARES), vm.vcpus),
            MEMORY_PROPERTY: per_unit(shares.get(MEMORY_SHARES), vm.memory_mb),
        }
        for name, value in values.items():
            if value is not None:
                vm_obj.with_property(f"vCommunity|{GROUP}|{name}", round(value, 2))
        if values[CPU_PROPERTY] is not None:
            vm_obj.with_metric(f"vCommunity|{GROUP}|{TEST_METRIC}", round(values[CPU_PROPERTY], 2))
    except Exception as e:
        logger.warning(f"Failed to publish the VM shares for : {vm_name} - {repr(e)}")
