# Business Applications

The pack calculates a performance value for each Business Application you define in VCF Operations, for each of its tiers, and for the Enterprise object. The **Critical Business Applications** dashboard shows them. Until you create at least one Business Application, these metrics have nothing to publish on.

The calculation is described in [Business Application Performance](../reference/metrics/business-application-performance.md).

## Create a Business Application

1. Go to **Workload Operations** > **Business Applications**.
2. Click **Add Applications** and choose **Define manually**.
3. Name the application. A useful first one is **VCF Appliances**, which holds the VCF appliances, including the NSX Edges.
4. Create one tier for each type of member, for example **NSX Edges**, **VCF Operations**, **vCenter Servers** and **NSX Managers**. Don't create sub-tiers.
5. Add the VMs to their tiers.

## How the pack reads the structure

- A Business Application is the parent of its tiers, and a tier is the parent of its VMs. The pack reads these relationships from VCF Operations in every collection cycle.
- **Tier Performance** is the average VM Guest OS KPI of the tier's VMs, so the VMs need the pack's VM metrics. A tier whose VMs are all powered off gets no new value.
- The **Business Application Performance** of an application is driven by its weakest tier, or by its Kubernetes namespaces when it has them.
- The pack reads the memberships and never writes them, so the ones you set in the editor are kept. Versions before 0.7.3 removed them, see [Membership is kept](../reference/metrics/business-application-performance.md#membership-is-kept).
- The values are calculated for every Business Application in VCF Operations, whichever vCenter its VMs run on. With several Adapter Instances, each one publishes the same values.

---

**Next:** [Summary Dashboards](summary-dashboards.md)
