# Future Enhancements

**Status: notes only. Not designed, not built.** Each item is a metric idea to be designed later. The enhancements also belong on the [To Do project](https://github.com/users/e1-rahabok/projects/1), one line each.

## Guest OS does not match vCenter

- **Object:** vSphere World
- **Metric:** Count of OS Difference
- **Description:** The number of virtual machines where the Guest OS seen by the guest does not match the Guest OS that vCenter shows. This can happen after a Guest OS upgrade or a reformat.
- **How to compare:** the Guest OS from vCenter, against the Guest OS from VMware Tools.
- **Note:** the names differ slightly between vCenter and the guest. Windows and Linux report themselves in their own words. The full list of names used by vCenter must be read first, to match them correctly.
- **Recommended action:** update the value in vCenter, so the two agree.

## Outdated VM hardware

- **Object:** vSphere World
- **Metric:** Outdated VM Hardware
- **Description:** The number of virtual machines whose VMX version is behind the minimum that Broadcom VMware supports. The count is absolute, not relative to each vCenter or ESXi host.
- **Note:** the minimum version has to be stored in an advanced setting, since it changes over time.
