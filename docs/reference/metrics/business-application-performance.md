# Business Application Performance

**Tier Performance**, **Business Application Performance** and **Business Applications Performance** score a business application at three levels: its tiers, the application itself, and the enterprise. Each is a 0-100 % value, and each is published only when it has data.

They replace the "Business Application Tier Performance", "Business Application Performance" and "Business Applications Performance" super metrics. Unlike a super metric, they need no manual enablement in the policy.

Code: [`Management Pack/app/metrics/container/business_app_performance.py`](../../../Management%20Pack/app/metrics/container/business_app_performance.py)

## The values

Published as metrics on the Container objects, in the group `vCommunity|Business Application`.

| Metric | On object | Calculation |
| :--- | :--- | :--- |
| `vCommunity\|Business Application\|Tier Performance` | Tier | The average of the **VM Guest OS KPI** of the Tier's VMs. |
| `vCommunity\|Business Application\|Business Application Performance` | Business Application (BusinessService) | The higher of two values: the **Performance** of its K8S Namespaces, and the **lowest Tier Performance** of its Tiers. |
| `vCommunity\|Business Application\|Business Applications Performance` | Enterprise | The average of the Business Applications of the Enterprise. |

The structure is read from VCF Operations: a Business Application is the parent of its Tiers, and a Tier is the parent of its VMs. The K8S Namespaces are the objects within two levels of a Business Application, as in the super metric.

## When there is no value

A value is published only when there is data for it. There is no 0 for "no data".

- **Tier:** no VM of the Tier has a VM Guest OS KPI. This happens when every VM is powered off, or its stats are older than 10 minutes. The Tier publishes nothing.
- **Business Application:** uses the namespaces and the Tiers that have a value. If there is neither, it publishes nothing. A Tier that publishes nothing is left out of the lowest Tier Performance, so one powered-off Tier does not pull the application to 0.
- **Enterprise:** uses the Business Applications that have a value. If none has one, it publishes nothing.

An Enterprise or Business Application value is not published when one of the relationships it needs cannot be read. Otherwise it would be built on part of the objects.

## Known limitations

> **Verify on the instance before you rely on the values.**

- **Not yet checked on a live system with real values.** The first live check published a constant (42) on the Tier objects. This is the first version that publishes the calculated values.
- **One cycle behind.** The VM KPIs of the current cycle are stored at the end of it, so these values use the stats of the last cycle, as the vSphere World metrics do.
- **Units.** All three are percent. The pack declares the object types and the metric with the percent unit, as it does for its VMware objects.
- **A value that stops being published is not cleared.** VCF Operations keeps the last value of a metric the pack no longer publishes, and the SDK has no way to publish "no value". Confirmed on the test instance: the probe value 42 stayed on all four Tiers after the probe was removed. So a Tier whose VMs are all powered off keeps its last value, not blank, until a fix is found.
- **Tier and namespace structure.** The Business Application uses the K8S Namespaces within two levels, and the Tiers as its direct children. If the topology of a business application differs, its value differs as well.
- **Business Applications with only namespaces** (modern applications, with no Tiers) use the namespace value alone.

## Replaces

| Removed super metric | Replaced by |
| :--- | :--- |
| Business Application Tier Performance | `vCommunity\|Business Application\|Tier Performance` |
| Business Application Performance | `vCommunity\|Business Application\|Business Application Performance` |
| Business Applications Performance | `vCommunity\|Business Application\|Business Applications Performance` |

The "Critical Business Applications" dashboard now uses these metrics.

[⬆ Back to top](#business-application-performance)
