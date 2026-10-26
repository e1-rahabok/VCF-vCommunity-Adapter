# Metrics

One page per metric the pack calculates. KPIs are metrics too. The full list of keys, by object type, is in [Metrics and Properties](../metrics-and-properties.md).

KPIs:

- [Cluster Performance](cluster-performance.md)
- [Cluster Risk](cluster-risk.md)
- [Cluster Consumption](cluster-consumption.md)
- [ESXi Performance](esxi-performance.md)
- [VM Performance](vm-performance.md)
- [Guest OS Performance](guest-os-performance.md)

Other metrics:

- [Periodic Cluster Check](periodic-cluster-check.md)
- [Network Speed Degradation](network-speed-degradation.md)
- [Operational Availability](operational-availability.md)
- [VM Shares](vm-shares.md)
- [vSphere World Cluster Metrics](vsphere-world-metrics.md)

Each page has its Known Limitations. The formula images the KPIs are built from are in [formula/](formula/).

## No stale values

Most of the pack's metrics are calculated from stats that VCF Operations already holds, read with its "latest" query. That query returns the last stored value **however old it is**: a host that is down or disconnected, or a VM that is powered off, keeps its last value as "latest".

The pack never uses such a value. A metric showing blank is better than one showing wrong data.

- **Stats** older than 10 minutes (two 5-minute collection cycles) are treated as **no data**. A metric that depends on them is not published for that cycle, and shows blank.
- **Properties** keep their last known value. VCF Operations stores a property only when it changes, so its last value is its current value.
- Two cycles, not one, so that a single late collection does not blank everything.
- The limit is `STALE_AFTER_MINUTES` in [`utils/ops_stats.py`](../../../Management%20Pack/app/utils/ops_stats.py).

### Two limits: 10 minutes, and 15 minutes for settings-based metrics

There are two limits, and each metric uses one of them. Nothing else.

| Limit | Applies to | Why | In code |
| :--- | :--- | :--- | :--- |
| **10 minutes** (the default) | Every metric, except those listed below. | Live values change between cycles. An old value would be wrong. | `STALE_AFTER_MINUTES` |
| **15 minutes** | Metrics based on **settings**, whose value is steady and changes rarely. Currently only **Number of Port Groups**, on the vCenter object and on vSphere World. | A port group count does not change between two cycles. A short gap in collection should not blank it. | `CONFIGURATION_STALE_AFTER_MINUTES` |

For the 15-minute metrics, the last known value is used for up to 15 minutes. After that it is treated as no data. On vSphere World, a vCenter whose count is older than 15 minutes is left out of the total, so the total falls when a vCenter stops reporting for that long. A vCenter that has never published the count is also left out.

The 15-minute limit is not a general rule. A metric is added to it only when its value is based on settings and changes rarely, and the metric is named in this section when it is.

> **Known limitation.** If the VMware vCenter adapter in VCF Operations is set to collect less often than every 10 minutes, every metric of this pack that depends on its stats is blank. A metric with the 15-minute limit is blank only after 15 minutes of that.
