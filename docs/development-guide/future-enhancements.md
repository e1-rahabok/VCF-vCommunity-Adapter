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

## Guest OS Uptime (%)

- **Object:** Virtual Machine
- **Metric:** Guest OS Uptime (%), in the `vCommunity|Availability` group
- **Purpose:** availability only, whether the base OS of the VM is up or down. Application, process and thread health are out of scope.
- **Status:** not designed in detail, not built. The logic below is the proposal. The open choices are marked **Decision**.

### Logic, per VM, per collection cycle (5 minutes)

1. **Powered off.** If the VM is not powered on (`summary|runtime|powerState` from VCF Operations), the value is 0. Stop.
2. **Heartbeat, read in bulk from vCenter** (`summary.quickStats.guestHeartbeatStatus`, already read every cycle):
   - **green:** the value is 100. Stop.
   - **red:** Tools is installed but the guest is not responding. The value is 0. Stop.
   - **yellow:** intermittent heartbeat. **Decision:** no value this cycle, or 100. The proposal is no value.
   - **gray:** Tools is not running or not installed. Go to step 3.
3. **No heartbeat: activity in the window.** Only VMs at step 3 are queried.
   - **Stable check.** A VM is stable when it is powered on, has no change of its published value in the last 12 cycles (one hour), and has all 12 values in VCF Operations. The values come from the stats read the adapter already does in bulk. A VM with fewer than 12 values is not stable.
   - **Schedule.** An unstable VM is queried every cycle. A stable VM is queried only on every 3rd cycle, so every 15 minutes. **Decision:** the 12-cycle window and the 3-cycle interval are proposals.
   - **Query.** One batched query for all VMs due in this cycle: vCenter `PerformanceManager.QueryPerf` with the 20-second realtime interval, the last 15 samples, and one counter, `cpu.usage.average`. This is a new vCenter call, not a repeat of the VCF Operations read. Its cost has not been measured.
   - **Slots.** The 15 samples are the 15 slots of the 300-second window. A slot is up when its CPU usage is above the floor. The floor is not yet calibrated on the lab.
   - **Value.** If at least one slot is up, the value is up slots ÷ 15 × 100. If no slot is up, there is no value, because silence does not prove the guest is down. **Decision:** whether a partial value is published, or only the full 100 when all 15 slots are up.
   - **Stable VM on a skipped cycle.** The value is not queried. **Decision:** hold the last published value, or publish no value.
4. **Publish.** `Guest OS Uptime (%)` with the value above, and the text property `Guest OS Uptime Source` with one of: `Powered off`, `Heartbeat green`, `Heartbeat red`, `Activity`, `No data`.

### Limitations

- **No value without Tools, unless the VM is active.** A VM with Tools not running and no CPU activity in the window has no value. Silence is not reported as down.
- **Activity is not proof of up.** A guest that is hung but spinning its CPU counts as up. The floor and the counter need calibrating on the lab.
- **The window is sampled, not watched.** Only 15 samples a cycle, and only on the cycles the VM is queried. A reboot between queried cycles can be missed.
- **Stable VMs are checked less often.** A stable VM that goes down is seen up to 15 minutes late, not 5.
- **The vCenter query adds load.** It is one batched call per cycle, but its effect on large vCenters is unmeasured.
- **Tools installed later changes the source.** Once Tools runs, the heartbeat decides, and the query stops for that VM.
