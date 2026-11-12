# Symptoms

Each section gives what you see, the cause, and what to do. If you have not run the checks in [First Steps](first-steps.md) yet, start there.

- Alerts: [A Collection Warnings alert is shown](#a-collection-warnings-alert-is-shown)
- Setup and connection: [The account never shows Collecting](#the-account-never-shows-collecting) · [The account is collecting, but the vCenter has no vCommunity values](#the-account-is-collecting-but-the-vcenter-has-no-vcommunity-values) · [Validate Connection fails](#validate-connection-fails) · [The certificate of vCenter changed](#the-certificate-of-vcenter-changed)
- Values: [A KPI or metric is blank](#a-kpi-or-metric-is-blank) · [Bad Network Packets or Network Speed Degradation is blank](#bad-network-packets-or-network-speed-degradation-is-blank) · [The Periodic Cluster Check or the Cluster Delta counts are late or blank](#the-periodic-cluster-check-or-the-cluster-delta-counts-are-late-or-blank)
- Configuration: [A configuration file change has no effect](#a-configuration-file-change-has-no-effect) · [No VM values after a change to the VM Options file](#no-vm-values-after-a-change-to-the-vm-options-file) · [Windows Service names are left out](#windows-service-names-are-left-out)
- Windows guests: [Windows properties, services or events are missing](#windows-properties-services-or-events-are-missing)
- Running: [Data stops after an upgrade](#data-stops-after-an-upgrade) · [Built-in views are missing or duplicated after an upgrade](#built-in-views-are-missing-or-duplicated-after-an-upgrade) · [Collection is slow](#collection-is-slow) · [The Cloud Proxy cannot start the adapter](#the-cloud-proxy-cannot-start-the-adapter)

---

## A Collection Warnings alert is shown

**What you see:** the alert **vCommunity Collection Warnings** is active on the vCenter object.

**Cause:** the pack logged warnings or errors in its recent collection cycles, so some values were not collected. When a value cannot be read, the pack logs it and publishes the rest of the cycle. The alert is how that shows up in VCF Operations. It is one alert for the whole collection, not one per value.

The alert fires when `vCommunity|Collection Health|Warnings in Last Cycle` on the vCenter object is above 0 for two cycles in a row, and clears after two cycles with no warnings. It ships turned off: to use it, activate **vCommunity Collection Warnings** in the policy that applies to your vCenter objects.

**What to do:**

1. On the vCenter object, read the property `vCommunity|Collection Health|First Warning`. It holds the first warning of the last cycle, cut to 250 characters, and names the object and the reason.
2. Search `adapter.log` on the Cloud Proxy for these words:
   - `Failed to`: one value could not be read for one object.
   - `Skipping`: one object was left out of this cycle.
   - `Unexpected collection error`: the whole cycle failed. A traceback follows.
3. Look the message up in [Log Messages](log-messages.md).

Some warnings are expected, such as a value that a host does not have. The alert tells you to read the first warning. It does not mean the pack is broken.

## The account never shows Collecting

**What you see:** under **Administration** > **Integrations** > **Accounts**, the account has no status, or it is not **Collecting** after 5 minutes.

**Cause:** the Cloud Proxy did not start the adapter, or the first collection failed. The pack runs only on a Cloud Proxy: see [How It Works](../installation-guide/how-it-works.md).

**What to do:**

1. Check that the Cloud Proxy is online and can reach the container registry, or your [dark site](../installation-guide/dark-site.md) registry.
2. Check that the Cloud Proxy can reach vCenter on port 443, or on the port set on the instance.
3. Click **Validate Connection**. See [Validate Connection fails](#validate-connection-fails).
4. If the account shows an error that starts with `No vCenter Adapter Instance found matching vCenter Server`, see the [next section](#the-account-is-collecting-but-the-vcenter-has-no-vcommunity-values).

## The account is collecting, but the vCenter has no vCommunity values

**What you see:** the account is **Collecting**, but no `vCommunity|` value appears on the vCenter objects.

**Cause:** the pack publishes onto the objects of the native vCenter adapter, and finds them by the vCenter address. If the **vCenter Server** field of the account differs from the address on the native vCenter Adapter Instance, the pack finds no vCenter and publishes nothing. The account then shows `No vCenter Adapter Instance found matching vCenter Server '…'`.

The other cause is that the native vCenter adapter has not collected the objects yet. The pack reads its objects and stats, so it needs them first.

**What to do:**

1. Compare the **vCenter Server** field of the account with the address on the native vCenter Adapter Instance, character by character. Use the same FQDN or IP. See [Adapter Instance](../configuration-guide/adapter-instance.md#11-account-details).
2. Check that the native vCenter adapter is collecting, and that its vCenter object exists.
3. Wait one collection cycle after the native adapter has collected.

## Validate Connection fails

**What you see:** **Validate Connection** shows an error.

**Cause:** the message names it. The common ones:

- A certificate message: the certificate does not match the thumbprint, or the Cloud Proxy does not trust it. The message says what to change. See [TLS and Security Settings](../configuration-guide/tls-and-security.md).
- `Pinned` without a thumbprint, or a thumbprint that is not SHA-256 or SHA-512. The pack refuses this setting rather than connecting without a check. Enter the thumbprint, or change the mode.
- A login error: the credential is wrong, or the account has no rights in vCenter.
- A network error: the Cloud Proxy cannot reach the address and port.

**What to do:** read the full message, fix what it names, and click **Validate Connection** again. The adapter log has the line `Unexpected connection test error`, followed by the traceback.

## The certificate of vCenter changed

**What you see:** the property `vCommunity|Certificate|Status` on the vCenter object reads `Changed`, and the adapter log has a warning with both thumbprints.

**Cause:** vCenter presents a different certificate from the one the pack recorded. After a planned certificate replacement this is expected.

**What to do:**

1. If the replacement was planned, do nothing. The pack records the new certificate, `Changed` clears after 24 hours, and the old thumbprint stays in `Previous SHA-256 Thumbprint`.
2. If it was not planned, check the certificate in vCenter before you trust it. Another server may be answering as vCenter.
3. With `Enabled` or `Pinned`, a changed certificate stops the connection. After you have checked the certificate, update the thumbprint or the trust. See [TLS and Security Settings](../configuration-guide/tls-and-security.md).

## A KPI or metric is blank

**What you see:** a KPI or a sub-metric has no value for an object, or its chart has a gap.

**Cause:** one of these. Check them in this order:

1. **The stat is not collected.** The pack reads the stats of the native vCenter adapter. If that adapter has no value for a stat, the KPI has no input. Check the same stat on the object in VCF Operations.
2. **The value is stale.** A stat older than 10 minutes counts as no data, so the metric is left blank instead of showing an old value. A disconnected host or a powered-off VM shows this. See [No stale values](../reference/metrics/README.md#no-stale-values).
3. **The sub-metric is skipped.** A sub-metric whose green range is marked "Excluded" is left out of the KPI while it is green. See [Skip when green](../concepts/kpi-scoring-models.md#skip-when-green).
4. **The sub-metric has no data.** It is left out of the KPI, never counted as 0. If no sub-metric has a value, the KPI is not published. See [Missing data](../concepts/kpi-scoring-models.md#missing-data).
5. **A metric or property the sub-metric needs is turned off in the policy.** See the next section.

**What to do:** find the object in VCF Operations, look at the input stat, and follow the cause that matches. If the log has `Failed to retrieve …` for the object, the reason is at the end of that line: see [Log Messages](log-messages.md).

## Bad Network Packets or Network Speed Degradation is blank

**What you see:** the Bad Network Packets sub-metric or the Network Speed Degradation metric has no value.

**Cause:** VCF Operations turns off some of the metrics and properties these need. See [Policy](../configuration-guide/policy.md).

**What to do:** activate the metrics listed on the policy page, in the Default Policy or the policy that applies to your hosts. Values appear from the next collection cycle.

## The Periodic Cluster Check or the Cluster Delta counts are late or blank

**What you see:** Close for Business or a Cluster Delta count has no new value after a window has ended, or shows an older value.

**Cause:** these values are calculated once per window, after every cluster has been calculated for it. Some cases are expected:

- **The first window after installing** has less history. The first Cluster Delta counts are 0, because there is no earlier window to compare with.
- **A large vCenter** needs several cycles to calculate all its clusters, so the value arrives a few cycles after the window ends. See [Periodic Cluster Check](../reference/metrics/periodic-cluster-check.md#known-limitations).
- **A cluster that cannot be read** stays due, and the Cluster Delta counts wait for it. The log has a `Stats query … failed with HTTP` warning for the failed read, and the `Periodic Cluster Check` lines show how many clusters are due.
- **A cluster with no KPI data** is not calculated. It has no Close for Business, and it is not counted in the Cluster Delta counts.

**What to do:** wait two cycles after the window ends. If the value is still missing, look for `Periodic Cluster Check` and `Cluster Delta counts` lines in the log, and check the Cluster Check settings on the account: see [Adapter Instance](../configuration-guide/adapter-instance.md#2-advanced-settings-optional).

## A configuration file change has no effect

**What you see:** you edited a configuration file, and the properties it lists do not change.

**Cause:** the account uses a different file from the one you edited, or the file has a problem. The pack reads the files at every collection, so no restart is needed.

**What to do:** see [Configuration Files](configuration-files.md). In short: check the file name set on the account, look for a `vCommunity configuration:` event on the vCenter object, and check that the file is valid XML.

## No VM values after a change to the VM Options file

**What you see:** after you added an entry to the VM Options file, VMs get no new `vCommunity|` values. VM Template objects are not updated either.

**Cause:** each entry in the VM Options file is a vSphere property path, such as `config.flags.diskUuidEnabled`, and the pack adds it to the request that reads every VM. If vSphere does not know the path, the whole request fails, so no VM is read that cycle. The log has `Invalid property requested for VirtualMachine: <path>`, followed by `Main data collection thread error in collect_vm_data`.

**What to do:** correct or remove the path named in the log, and save the file. Check the path in the vCenter Managed Object Browser, under a VM's `config` object. See [Configuration Files](configuration-files.md#the-format).

## Windows Service names are left out

**What you see:** the log has the warning `Windows Service names left out because they contain characters that are not allowed`, and some services are not checked.

**Cause:** a name in the Windows Service configuration file has a character the pack does not put in a command line. Only letters, digits, space and `_ . $ # @ ( ) + -` are allowed. The other names are still checked.

**What to do:** check the service name in the Windows Services list of the VM, and use it as Windows shows it. A service whose name has other characters cannot be checked by this pack.

## Windows properties, services or events are missing

**What you see:** some VMs have no Windows services, OS information or Windows events.

**Cause:** the pack runs a PowerShell script inside the guest through the vSphere Guest API. That needs all of these:

- VMware Tools running in a Windows guest.
- A Windows user name and password on the account's credential, with rights to run the script. For event logs, the account must be in the local `Event Log Readers` group. See [System Requirements](../installation-guide/system-requirements.md).
- The monitoring turned on. **Guest OS Service Monitoring Status** and **Windows Event Log Monitoring Status** are `Disabled` by default. The OS information is collected only when Guest OS Service Monitoring is `Enabled`. See [Adapter Instance](../configuration-guide/adapter-instance.md#2-advanced-settings-optional).
- The ESXi host certificate accepted. With **Guest File Transfer TLS Validation** at `Pinned` or `Strict`, a host whose certificate differs from vCenter's record is refused, and nothing is sent to the VM.
- Time left in the cycle. Guest work is limited to 30 minutes per cycle. VMs after that point wait for the next cycle.

The log tells you which one:

| Log line | Meaning |
| :--- | :--- |
| `… The certificate of the ESXi host does not match the thumbprint that vCenter records for it, so nothing was sent` | The host certificate was refused. It appears after `Exception during file transfer to <vm>:`, `Exception during file creation on <vm>:` or `Windows Service monitoring failed on <vm>:`. |
| `File transfer failed to <vm>: <status> - <reason>` | The ESXi host answered the file transfer with an error status. Check the Windows credential and VMware Tools. |
| `Command execution failed on <vm>`, at the end of a `Windows Service monitoring failed on <vm>:`, `Windows OS information failed on <vm>:` or `An error occurred during Windows Event Log collection on <vm>:` line | The script did not start in the guest. Check VMware Tools and the Windows credential. |
| `The guest time budget of 30 minutes for this collection is spent.` | The remaining VMs are read in the next cycle. |

**What to do:** fix what the log line names, then wait one cycle. [Log Messages](log-messages.md#windows-guests) lists the other guest messages.

## Data stops after an upgrade

**What you see:** after you install a new version, the account stops collecting, or its data stops.

**Cause:** Adapter Instances often stop collecting after an upgrade until their collection is restarted.

**What to do:** restart the collection of the account: see [After an Upgrade: Restart Collection](../installation-guide/installation.md#after-an-upgrade-restart-collection).

## Built-in views are missing or duplicated after an upgrade

**What you see:** after you upgrade from version 0.8.1 or earlier, built-in views are gone on VCF Operations 9.0.2 or 9.1.1, and dashboards or reports that use them show "The view does not exist". On 8.18.7, views of the pack appear twice with the same title.

**Cause:** those versions shipped 117 views under the ids of built-in views. See [Upgrade From a Version That Shipped Built-in View Ids](../installation-guide/installation.md#upgrade-from-a-version-that-shipped-built-in-view-ids).

**What to do:** on 9.0.2 and 9.1.1, import the views from a content export of a clean instance of the same version. On 8.18.7 the duplicates are the old copies, and they are deleted when the pack is uninstalled.

## Collection is slow

**What you see:** values arrive late, or a cycle takes longer than 5 minutes.

**Cause:** the work grows with the inventory and with what is turned on:

- **ESXi software packages** need one call to each host, which makes them the slowest data in the pack. See [Adapter Instance](../configuration-guide/adapter-instance.md).
- **Windows checks** run a script in each Windows VM, so each VM adds time.
- **Content libraries** are read with one request per library item.
- **A large vCenter** has more objects per cycle.

**What to do:** the end of each cycle in the log has a `Collection Timing Summary` with the time of each part. Turn off what you don't need: the Windows checks are switched off on the account, and an empty ESXi software packages file collects no packages (see [Configuration Files](configuration-files.md#the-format)). Check the summary again after one cycle.

## The Cloud Proxy cannot start the adapter

**What you see:** the account does not start, and the Cloud Proxy shows an error about the image.

**Cause:** the Cloud Proxy cannot pull the adapter's container image, either from the public registry or from your private registry on a dark site. See [How It Works](../installation-guide/how-it-works.md) and [Dark Site Installation](../installation-guide/dark-site.md).

**What to do:** check the Cloud Proxy's access to the registry. On a dark site, check that the image is in the private registry.

---

**Next:** [Configuration Files](configuration-files.md) · [Log Messages](log-messages.md)
