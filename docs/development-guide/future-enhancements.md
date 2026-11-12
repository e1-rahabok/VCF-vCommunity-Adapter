# Future Enhancements

**Status: ideas only, not designed or built.** Each item is a metric to design later. Every item also belongs on the [To Do project](https://github.com/users/e1-rahabok/projects/1), as one line that links here.

## Guest OS does not match vCenter

- **Object:** vSphere World
- **Metric:** Count of OS Difference
- **Description:** the number of VMs where the guest OS reported by the guest differs from the guest OS configured in vCenter. This can happen after a guest OS upgrade or a reinstall.
- **How to compare:** the guest OS from vCenter against the guest OS from VMware Tools.
- **Note:** vCenter and the guest name the OS slightly differently, because Windows and Linux describe themselves in their own words. Read the full list of names that vCenter uses first, to match them correctly.
- **Recommended action:** update the guest OS in vCenter so the two agree.

## Outdated VM hardware

- **Object:** vSphere World
- **Metric:** Outdated VM Hardware
- **Description:** the number of VMs whose hardware (VMX) version is older than the minimum that Broadcom supports. The count is absolute, not relative to each vCenter or ESXi host.
- **Note:** the minimum version changes over time, so store it in an Adapter Instance setting.
- **Partly covered today:** the view **VM Outdated Hardware Version** ([`content/reports/VM Outdated Hardware Version vCommunity.xml`](../../Management%20Pack/content/reports/VM%20Outdated%20Hardware%20Version%20vCommunity.xml)) lists the VMs whose hardware version is not 21 or 22. The versions are fixed in the view, and there is no metric or count.
