# VM Shares

**Share per vCPU** and **Share per MB of Memory** divide the CPU and memory shares of a VM by its size, so that VMs of different sizes can be compared. Shares matter only under contention: a VM above Normal then gets more than its fair part, and a VM below Normal gets less.

They replace the "Share per vCPU" and "Share per GB of Memory" super metrics. Unlike the super metrics, they need nothing enabled in the policy.

Code: [`Management Pack/app/properties/vm/vm_shares.py`](../../../Management%20Pack/app/properties/vm/vm_shares.py)

## Known limitations

> **Read this before you use the values.**

- **They are metrics until issue #49 is fixed.** The shares are meant to be properties, because they change only with the VM's configuration (see [Design considerations](#design-considerations)). VCF Operations showed no value when they were published as properties, so they are published as metrics with no unit, under the same names. A metric gets a point every collection cycle, so its chart is a line rather than a single value. Properties published by earlier versions stay in VCF Operations under their old names and are no longer updated. See [GitHub issue #49](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/49).
- **No unit.** VCF Operations does not accept `count` as the unit of these metrics, so they have none.
- **Inputs read as stats are not used when stale.** When VCF Operations stores the shares as stats rather than properties, a value older than 10 minutes counts as no data. See [No stale values](README.md#no-stale-values).
- **The memory value is per MB.** The super metric was named "Share per GB of Memory", but it calculated shares ÷ memoryKB × 1024, which is per MB. The values are the same as before, under the correct name. Normal is 10.
- **No value when VCF Operations has no vCPU count, memory size or shares for the VM.** This avoids a division by zero.
- **Custom shares are compared as they are.** The Low, Normal and High values below apply to the standard share levels only. A VM with custom shares can have any value.

## The values

Published as metrics on every VM, powered on or off, in the VM's `vCommunity|Configuration` group next to the share levels.

| Metric | Calculation | Low | Normal | High |
| :--- | :--- | :--- | :--- | :--- |
| `vCommunity\|Configuration\|Share per vCPU` | CPU shares ÷ vCPUs | 500 | 1000 | 2000 |
| `vCommunity\|Configuration\|Share per MB of Memory` | Memory shares ÷ configured memory in MB | 5 | 10 | 20 |

The inputs come from VCF Operations, as in the super metrics: `config|cpuAllocation|shares|shares`, `config|memoryAllocation|shares|shares`, `config|hardware|numCpu` and `config|hardware|memoryKB`.

## Design considerations

- **Properties by design.** Shares change only when the VM's configuration changes. They are a setting, not a measurement over time. VCF Operations stores a property only when it changes, so a property avoids a point every 5 minutes for a value that does not move. Until issue #49 is fixed they are metrics.
- **Calculated in code**, so the values are there as soon as the pack is installed, without enabling anything in the policy.
- **Every VM, powered on or off.** Shares are configuration, and they apply as soon as the VM is powered on.
- **Read once per cycle for all VMs.** The shares are read in one request, and the vCPU count and memory size are already read for the KPIs. The shares are read as properties, or as stats when VCF Operations stores them as stats.
- All inputs come from VCF Operations. Nothing is read from vCenter.

## Example

A VM with 4 vCPUs and 16 GB at Normal has 4,000 CPU shares and 163,840 memory shares: Share per vCPU = 1,000, and Share per MB of Memory = 10.

The tests in [`Management Pack/tests/test_vm_shares.py`](../../../Management%20Pack/tests/test_vm_shares.py) check the same example.
