# Business Application Performance

**Tier Performance**, **Business Application Performance** and **Business Applications Performance** score a business application at three levels: its tiers, the application, and the enterprise. Each is a 0 to 100 % value, published only when it has data.

They replace the "Business Application Tier Performance", "Business Application Performance" and "Business Applications Performance" super metrics. Unlike the super metrics, they need nothing enabled in the policy.

Code: [`Management Pack/app/metrics/container/business_app_performance.py`](../../../Management%20Pack/app/metrics/container/business_app_performance.py)

## The values

Published as metrics on the Container objects, in the group `vCommunity|Business Application`.

| Metric | On object | Calculation |
| :--- | :--- | :--- |
| `vCommunity\|Business Application\|Tier Performance` | Tier | The average [VM Guest OS KPI](vm-performance.md#vm-guest-os-kpi) of the Tier's VMs. |
| `vCommunity\|Business Application\|Business Application Performance` | Business Application (BusinessService) | The highest of these values: the **Performance** of each of its K8S Namespaces, and the **lowest Tier Performance** of its Tiers. |
| `vCommunity\|Business Application\|Business Applications Performance` | Enterprise | The average of the Business Applications of the Enterprise. |

The structure is read from VCF Operations: a Business Application is the parent of its Tiers, and a Tier is the parent of its VMs. The K8S Namespaces of a Business Application are those within two levels below it, as in the super metric.

The pack reads the Container objects of every adapter instance, so each Adapter Instance of the pack publishes the same values.

## When there is no value

A value is published only when there is data for it. The pack never publishes 0 to mean "no data".

- **Tier:** publishes nothing when none of its VMs has a VM Guest OS KPI, for example when every VM is powered off or its stats are older than 10 minutes.
- **Business Application:** uses the namespaces and the Tiers that have a value, and publishes nothing if there are none. A Tier without a value is left out of the lowest Tier Performance, so one powered-off Tier does not pull the application to 0.
- **Enterprise:** uses the Business Applications that have a value, and publishes nothing if none has one.

## Known limitations

- **A failed read stops the rest of the cycle.** The relationships are read one object at a time. If one read fails, the Business Application collection stops for that cycle: values already added are published, and the rest are not, including unrelated applications and enterprises. A failure while reading the Tiers' VMs means no Tier values at all. The adapter log has `Business Application performance failed`, and the next cycle tries again.
- **One cycle behind.** The VM KPIs of the current cycle are stored at the end of it, so these values use the KPIs of the previous cycle, as the vSphere World metrics do.
- **A value that stops being published is not cleared.** VCF Operations keeps the last value of a metric the pack no longer publishes, and the SDK cannot publish "no value". A Tier whose VMs are all powered off keeps its last value instead of going blank.
- **Tier and namespace structure.** The Business Application uses the K8S Namespaces within two levels below it, and its direct child Tiers. A business application built differently gets a different value.
- **Business Applications with only namespaces**, such as modern applications without Tiers, use the namespace values alone.
- **Live checks.** The [live validation](../../../tools/validate/validate.md) checks that the three metrics are present on the test instance. Compare a few values with the VM Guest OS KPI of their VMs before you rely on them.
- **Units.** All three are in percent, declared in the adapter definition on each of the three object types.

## Membership is kept

The membership of a Business Application (its Tiers), of a Tier (its VMs) and of an Enterprise (its Business Applications) is set by hand in the Business Applications editor. The pack reads it and never writes it.

The pack sends its own relationships, for Content Library and Library Item objects, with the `PER_OBJECT` update mode. Only the child lists of the objects in its result are replaced, so the memberships that people set by hand are kept. With the platform's default mode, every relationship missing from the result is removed, which silently deleted these memberships in versions before 0.7.3. As a consequence, the pack does not write a link from a Content Library to its vCenter, or from a VM Template to its folder. See [Template and Content Library Design](../../development-guide/template-and-library-design.md#parent-and-child-relationships).

If a membership disappears, check first that the pack is version 0.7.3 or later.

## Replaces

| Removed super metric | Replaced by |
| :--- | :--- |
| Business Application Tier Performance | `vCommunity\|Business Application\|Tier Performance` |
| Business Application Performance | `vCommunity\|Business Application\|Business Application Performance` |
| Business Applications Performance | `vCommunity\|Business Application\|Business Applications Performance` |

The Critical Business Applications dashboard uses these metrics.
