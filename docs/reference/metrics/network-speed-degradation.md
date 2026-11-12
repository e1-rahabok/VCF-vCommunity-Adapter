# Network Speed Degradation

**Network Speed Degradation** shows whether the physical NICs of an ESXi host run at the speed they are configured for. A NIC that negotiates a lower speed, such as 1 Gbps on a 10 Gbps link after a cable or switch port problem, still passes traffic, so the problem is easy to miss.

It replaces the "Network Speed Degradation" and "Total Network Speed Degradation" super metrics and fixes problems in their formulas. See [Changes from the super metrics](#changes-from-the-super-metrics).

Code: one file per object type: [host](../../../Management%20Pack/app/metrics/host/host_network_speed.py), [Datacenter](../../../Management%20Pack/app/metrics/datacenter/datacenter_network_degradation.py), [vSphere World](../../../Management%20Pack/app/metrics/world/vsphere_network_degradation.py), and [vCenter](../../../Management%20Pack/app/metrics/vcenter/vcenter_network_speed.py), which reads the hosts of one vCenter.

## Known limitations

> **Read this before you use the metrics.**

- **It needs a value that is deactivated by default.** `net|configuredSpeed` must be activated in the policy, with **Instanced State** on, so there is one value per NIC. Without it there is no result. See [Policy](../../configuration-guide/policy.md).
- **Both NIC speeds are read with the latest-stats query.** The pack asks VCF Operations for `net|speed` and `net|configuredSpeed` through `api/resources/stats/latest/query`, one value per NIC instance. A NIC whose speeds VCF Operations does not return through that query has no value.
- **Stats older than 10 minutes count as no data**, so the metric is blank rather than based on old values. See [No stale values](README.md#no-stale-values).
- **A NIC set to auto-negotiate is left out.** When a NIC's configured speed is "Auto negotiate" in vCenter, VCF Operations has no `net|configuredSpeed` for it, so there is nothing to compare its actual speed with. A host whose NICs all auto-negotiate has no value and is not counted. To include such a NIC, set it to a fixed speed on the host in vCenter.
- **A NIC that is down is not counted as degraded.** A speed of 0 means the NIC is down or unused, which is a different problem from running slower. It is left out.
- **Hosts without a value are not counted in Total Network Speed Degradation.** The count is a lower bound: hosts that could not be checked may also be degraded.
- **A host is matched to its Datacenter by name**, from the host property `summary|parentDatacenter`. A host without that property is not counted for any Datacenter.
- **The vSphere World count can be one collection cycle old (5 minutes).** It is built from the host values already stored in VCF Operations, like the other [vSphere World metrics](vsphere-world-metrics.md#known-limitations). Every Adapter Instance publishes the same count.
- **When VCF Operations returns no NIC speed for any host, nothing is published for that cycle.** The request has failed, and a count of 0 would be false assurance.

## The metrics

| Object | Metric | Calculation |
| :--- | :--- | :--- |
| ESXi host | `vCommunity\|Network\|Network Speed Degradation` (%) | Sum of the actual NIC speeds ÷ sum of the configured NIC speeds × 100, over the NICs that can be compared. 100 % means no degradation. Capped at 100 %. |
| Datacenter | `vCommunity\|Network\|Total Network Speed Degradation` (count) | The number of hosts in the Datacenter below 100 %, from the same collection cycle. |
| vSphere World | `vCommunity\|Network\|Total Network Speed Degradation` (count) | The number of hosts below 100 %, across all vCenters. |

The inputs are, per physical NIC and in Mbps, `net|speed` (the speed the NIC runs at) and `net|configuredSpeed`. VCF Operations returns one value per NIC, such as `net:vmnic0|speed`, and the pack compares each NIC with its own configured speed.

## Design considerations

- **Each NIC is checked on its own.** The super metric averaged all speeds and all configured speeds, so a NIC that was down looked like degradation, and a NIC without a configured speed made the result wrong.
- **A host with no NIC left to compare has no value**, instead of a division by zero.
- **Read once per cycle per vCenter**, before the collectors run, for the host and Datacenter values.
- All inputs come from VCF Operations. Nothing is read from vCenter.

## Examples

| NICs (actual / configured, Mbps) | Value |
| :--- | :--- |
| 10000 / 10000, 10000 / 10000 | 100 % |
| 1000 / 10000, 10000 / 10000 | (1000 + 10000) ÷ (10000 + 10000) = 55 % |
| 0 / 10000 (down), 10000 / 10000 | 100 %: the NIC that is down is left out |
| 10000 / 0 (no configured speed) | no value |

The tests in [`Management Pack/tests/test_network_speed_degradation.py`](../../../Management%20Pack/tests/test_network_speed_degradation.py) check the same examples.

## Changes from the super metrics

| Problem in the super metric | Fix |
| :--- | :--- |
| `avg(net\|speed) / avg(net\|configuredSpeed)`: a NIC that was down (speed 0) pulled the average down, as if it were degraded. | Each NIC is compared with its own configured speed. A NIC that is down is left out. |
| A host without a configured speed divided by zero. | NICs without a configured speed are left out. A host with none left has no value. |
| The count on Datacenter and vSphere World was a super metric over the host super metric. | Calculated in code: per Datacenter from the same cycle, and on vSphere World from the stored host values. |
