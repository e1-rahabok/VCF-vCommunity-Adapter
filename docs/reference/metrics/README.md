# Metrics

How the pack calculates its metrics and KPIs. A KPI is a metric too: a 0 to 100 % score built from sub-metrics. Every key the pack publishes, by object type, is in [Metrics and Properties](../metrics-and-properties.md). Metrics that are simple counts or values read from vCenter, such as DRS Score, the resource pool counts, Collection Health and the content library counts, are described only there.

KPIs:

- [Cluster Performance](cluster-performance.md)
- [Cluster Risk](cluster-risk.md)
- [Cluster Consumption](cluster-consumption.md)
- [ESXi Performance](esxi-performance.md)
- [VM Performance](vm-performance.md), with the VM Guest OS KPI
- [Guest OS Performance](guest-os-performance.md)

Other metrics:

- [Periodic Cluster Check](periodic-cluster-check.md)
- [Network Speed Degradation](network-speed-degradation.md)
- [Operational Availability](operational-availability.md)
- [VM Shares](vm-shares.md)
- [Business Application Performance](business-application-performance.md)
- [vSphere World Cluster Metrics](vsphere-world-metrics.md)

How every KPI scores and combines its sub-metrics is in [KPI Scoring Models](../../concepts/kpi-scoring-models.md#how-the-pack-scores-a-kpi). The source tables of the KPI limits are in [formula/](formula/).

## No stale values

Most metrics are calculated from stats that VCF Operations already holds, read with its "latest" query. That query returns the last stored value however old it is. A host that is down or disconnected, or a VM that is powered off, keeps its last value as "latest".

The pack does not use such values. It leaves a metric blank rather than publish a number built on old data.

- A stat older than 10 minutes, two 5-minute collection cycles, counts as no data. A metric that depends on it is not published for that cycle.
- Two cycles rather than one, so that a single late collection does not blank everything.
- Properties keep their last known value. VCF Operations stores a property only when it changes, so its last value is its current value.
- The limit is `STALE_AFTER_MINUTES` in [`utils/ops_stats.py`](../../../Management%20Pack/app/utils/ops_stats.py).

### Two limits: 10 minutes, and 15 minutes for settings-based metrics

Metrics built from the "latest" stats use one of two limits:

| Limit | Applies to | Why | In code |
| :--- | :--- | :--- | :--- |
| 10 minutes (the default) | Every metric built from latest stats, except the one below. | Live values change between cycles, so an old value would be wrong. | `STALE_AFTER_MINUTES` |
| 15 minutes | Metrics based on settings, which change rarely. Today only **Number of Port Groups** on vSphere World, which adds up the vCenters' stored counts. | A port group count does not change between two cycles, so a short gap in collection should not blank the total. | `CONFIGURATION_STALE_AFTER_MINUTES` |

On vSphere World, a vCenter whose port group count is older than 15 minutes, or that has never published one, is left out of the total. The total therefore falls when a vCenter stops reporting for that long. A metric is added to the 15-minute limit only when its value comes from settings and changes rarely, and it is then listed here.

Two other groups do not use these limits:

- **Window history.** The [Periodic Cluster Check](periodic-cluster-check.md) and the Cluster Delta counts read the 5-minute samples of a past window, not the latest value. Each sample belongs to its own time, so age does not apply.
- **Values read from vCenter.** DRS Score, the SCSI controller count, the license Remaining Days, the content library metrics, the vCenter Number of Port Groups and Collection Health are read from vCenter, or from the adapter itself, in the same cycle they are published.

> **Limitation.** If the VMware vCenter adapter in VCF Operations collects less often than every 10 minutes, every metric of this pack that depends on its stats is blank. A metric with the 15-minute limit goes blank only after 15 minutes.
