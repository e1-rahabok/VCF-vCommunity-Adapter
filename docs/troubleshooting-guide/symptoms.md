# Symptoms

Each section starts with what you see, then the cause, then what to do. Start with [First Steps](first-steps.md) if you have not run its checks yet.

**On this page:**

- Alerts: [A Collection Warnings alert is shown](#a-collection-warnings-alert-is-shown)
- Setup and connection: [The account never shows Collecting](#the-account-never-shows-collecting) · [The account is collecting, but the vCenter has no vCommunity values](#the-account-is-collecting-but-the-vcenter-has-no-vcommunity-values) · [Validate Connection fails](#validate-connection-fails) · [The certificate of vCenter changed](#the-certificate-of-vcenter-changed)
- Values: [A KPI or metric is blank](#a-kpi-or-metric-is-blank) · [Bad Network Packets or Network Speed Degradation is blank](#bad-network-packets-or-network-speed-degradation-is-blank) · [The Periodic Cluster Check or the Cluster Delta counts are late or blank](#the-periodic-cluster-check-or-the-cluster-delta-counts-are-late-or-blank)
- Configuration: [A configuration file change has no effect](#a-configuration-file-change-has-no-effect) · [Windows Service names are left out](#windows-service-names-are-left-out)
- Windows guests: [Windows properties, services or events are missing](#windows-properties-services-or-events-are-missing)
- Running: [Data stops after an upgrade](#data-stops-after-an-upgrade) · [Collection is slow](#collection-is-slow) · [The Cloud Proxy cannot start the adapter](#the-cloud-proxy-cannot-start-the-adapter)

---

## A Collection Warnings alert is shown

**What you see:** the alert **vCommunity Collection Warnings** is active on the vCenter object. It means the last collection cycle wrote warnings or errors. Some values were not collected, and nothing else is shown.

**Cause:** the alert is raised on purpose, for any warning or error in a cycle. A value that cannot be read is logged, and the rest of the cycle is still published, so the alert is the only visible sign. It is one alert for the whole collection, not one per value.

**What to do:**

1. On the vCenter object, read the property `vCommunity|Collection Health|First Warning`. It is the first warning of the last cycle, and it names the object and the reason.
2. Search `adapter.log` on the Cloud Proxy for these keywords:
   - `Failed to`: one value could not be read for one object.
   - `Skipping`: one object was left out of this cycle.
   - `Unexpected collection error`: the whole cycle failed, and a traceback follows.
3. The metric `vCommunity|Collection Health|Warnings in Last Cycle` shows how many warnings the cycle wrote. The alert clears when a cycle has none.

Some warnings are expected, such as a value that a host does not have. The alert is a prompt to read the first warning, not a sign that the pack is broken. See [Log Messages](log-messages.md).

## The account never shows Collecting

**What you see:** under **Administration** → **Integrations** → **Accounts**, the account has no status, or it does not change to **Collecting** after 5 minutes.

**Cause:** the Cloud Proxy did not start the adapter, or the first collection failed. The pack collects through the Cloud Proxy only, see [How It Works](../installation-guide/how-it-works.md).

**What to do:**

1. Check that the Cloud Proxy is online, and that it can reach the container registry, or your [dark site](../installation-guide/dark-site.md) registry.
2. Check that the Cloud Proxy can reach vCenter on port 443 (or the port of the instance).
3. Click **Validate Connection**, see [below](#validate-connection-fails).
4. If the account shows an error that starts with `No vCenter Adapter Instance found matching vCenter Server`, go to [the next symptom](#the-account-is-collecting-but-the-vcenter-has-no-vcommunity-values).

## The account is collecting, but the vCenter has no vCommunity values

**What you see:** the account says **Collecting**, but no `vCommunity|` value appears on the vCenter objects.

**Cause:** the pack matches its objects to the objects of the native vCenter adapter by the vCenter address. The address must be the same as the one of the native vCenter Adapter Instance. If it is not, the pack finds no vCenter, and publishes nothing. The account shows `No vCenter Adapter Instance found matching vCenter Server '…'`.

The other cause is that the native vCenter adapter has not collected the objects yet. The pack reads its objects and stats, so it needs them first.

**What to do:**

1. Compare the **vCenter Server** field of the account with the address of the native vCenter Adapter Instance, character by character. Use the same FQDN or IP. See [Adapter Instance](../configuration-guide/adapter-instance.md#11-account-details).
2. Check that the native vCenter adapter collects, and that its vCenter object exists.
3. Wait one collection cycle after the native adapter has collected.

## Validate Connection fails

**What you see:** **Validate Connection** shows an error.

**Cause:** the message says which one. The common causes are:

- **A certificate message:** the certificate does not match the thumbprint, or the Cloud Proxy does not trust it. The message says what to change. See [TLS and Security Settings](../configuration-guide/tls-and-security.md).
- **`Pinned` without a thumbprint, or a thumbprint that is not SHA-256 or SHA-512:** the setting is refused on purpose, so that it is never taken as "no check". Enter the thumbprint, or change the mode.
- **A login error:** the credential of the account is wrong, or the account has no rights in vCenter.
- **A network error:** the Cloud Proxy cannot reach the address and port.

**What to do:** read the full message. Fix the item it names, then click **Validate Connection** again. The message is also in the adapter log, as `Unexpected connection test error`.

## The certificate of vCenter changed

**What you see:** the property `vCommunity|Certificate|Status` on the vCenter object reads `Changed`, and the adapter log has a warning with both thumbprints.

**Cause:** the certificate of vCenter is different from the one recorded before. This is expected after a planned certificate replacement. It is unexpected otherwise.

**What to do:**

1. If the replacement was planned, do nothing. The pack then watches the new certificate, `Changed` clears after 24 hours, and the old thumbprint stays in the property `Previous SHA-256 Thumbprint`.
2. If it was not planned, check the certificate of vCenter before you trust it. Something else may be answering as vCenter.
3. If you use `Enabled` or `Pinned`, a changed certificate stops the connection. Set the thumbprint or the trust after you have checked it. See [TLS and Security Settings](../configuration-guide/tls-and-security.md).

## A KPI or metric is blank

**What you see:** a KPI, or a sub-metric, has no value for an object, or has a gap in its chart.

**Cause:** one of these, in the order to check:

1. **The stat is not collected.** The pack reads the stats of the native vCenter adapter. If the vCenter adapter has no value for a stat, the KPI has no input. Check the same stat on the object in VCF Operations.
2. **The value is stale.** A stat older than 10 minutes counts as no data, so the metric is left blank rather than showing an old value. A host that is disconnected, or a VM that is powered off, does this. This is by design, see [Metrics and Properties](../reference/metrics-and-properties.md).
3. **The sub-metric is skipped.** A sub-metric in its "Excluded" green is left out, and a KPI with no other input has no value. See [How the pack scores a KPI](../concepts/kpi-scoring-models.md#skip-when-green).
4. **The sub-metric is missing data.** A sub-metric with no value is left out of the KPI, never counted as 0. If no sub-metric has a value, the KPI is not published. See [Missing data](../concepts/kpi-scoring-models.md#missing-data).
5. **A property the sub-metric needs is deactivated in VCF Operations.** See the next symptom.

**What to do:** find the object in VCF Operations, look at its stat, and follow the number above that matches. If the pack's log says `Failed to retrieve …` for the object, the reason is in that line: see [Log Messages](log-messages.md).

## Bad Network Packets or Network Speed Degradation is blank

**What you see:** the Bad Network Packets sub-metric, or the Network Speed Degradation metric, has no value.

**Cause:** VCF Operations deactivates some metrics and properties by default. The pack needs them. See [Policy](../configuration-guide/policy.md).

**What to do:** activate the metrics named in the policy page on the Default Policy, or on the policy that applies to your hosts. Values appear from the next collection cycle.

## The Periodic Cluster Check or the Cluster Delta counts are late or blank

**What you see:** Close for Business, or a Cluster Delta count, shows no new value after a window has ended, or shows an older value.

**Cause:** these values are calculated once per window, after every cluster has been calculated for it. Expected cases:

- **The first window** after installing has less history, and the first Cluster Delta counts are 0 because there is no earlier window to compare with.
- **A large vCenter** takes several cycles to calculate all its clusters. The value comes a few cycles after the window ends. See [Periodic Cluster Check](../reference/metrics/periodic-cluster-check.md#known-limitations).
- **A cluster that cannot be read** stays due. The Cluster Delta counts then wait for it, and the value does not come until it is calculated. The log shows a `Stats query … failed with HTTP` warning for the failed read, and the `Periodic Cluster Check` lines show how many clusters are due.
- **A cluster without KPI data** is not calculated, and it has no Close for Business. Its value is blank, and it is not counted in the Cluster Delta counts.

**What to do:** wait for two cycles after the window end. If the value is still missing, look in the log for `Periodic Cluster Check` lines. Check the Cluster Check settings on the account are the ones you expect, see [Adapter Instance](../configuration-guide/adapter-instance.md#2-advanced-settings-optional).

## A configuration file change has no effect

**What you see:** you edited a configuration file, and the properties it lists do not change.

**Cause:** the file the account uses is not the one you edited, or the file has a problem. The pack reads the file at each collection, with no restart needed.

**What to do:** see [Configuration files](configuration-files.md). In short: check the name of the file set on the account, check the vCenter object for a `vCommunity configuration:` event, and check that the file is valid XML.

## Windows Service names are left out

**What you see:** the log has a warning, `Windows Service names left out because they contain characters that are not allowed`, and some services are not checked.

**Cause:** a service name in the Windows Service configuration file has a character that the pack does not allow in a command. Only letters, digits, space, and `_ . $ # @ ( ) + -` are allowed. The others are left out, and the rest are checked.

**What to do:** check the name of the service in the Windows Services list of the VM. Use the name as Windows shows it. Names with other characters cannot be checked by this pack.

## Windows properties, services or events are missing

**What you see:** Windows services, the OS information, or the Windows event logs of some VMs have no values.

**Cause:** the pack runs a PowerShell script inside the guest, through the vSphere Guest API. It needs:

- **VMware Tools** running in the guest.
- **A Windows credential** on the Adapter Instance, with rights to run the script. For event logs, the account must be a member of `Event Log Readers`. See [System Requirements](../installation-guide/system-requirements.md).
- **The monitoring turned on.** Windows Service and Windows Event Log monitoring are off by default. See [Adapter Instance](../configuration-guide/adapter-instance.md#2-advanced-settings-optional).
- **The ESXi certificate accepted,** when the guest file transfer is `Pinned`. A host with a different certificate is refused, and the script is not sent.

The log says which one: `Command execution failed on <vm>` means the script did not start, usually VMware Tools or the credential. `File transfer failed to <vm>` means the transfer was refused, usually the certificate or the credential.

**What to do:** fix the item in the log line, then wait one cycle.

## Data stops after an upgrade

**What you see:** after installing a new version, the account stops collecting, or its data stops.

**Cause:** the Adapter Instances usually stop after an upgrade, until their collection is restarted.

**What to do:** restart the collection of the account, see [After an Upgrade: Restart Collection](../installation-guide/installation.md#after-an-upgrade-restart-collection).

## Collection is slow

**What you see:** the values arrive late, or a cycle takes longer than the 5-minute cycle.

**Cause:** the amount of work is proportional to the inventory and to what is turned on:

- **ESXi software packages** need a call to each host. This is the slowest data in the pack. See [Adapter Instance](../configuration-guide/adapter-instance.md).
- **Windows checks** run a script in each VM. Each VM adds time. See the last point above.
- **A large vCenter** has more objects per cycle.

**What to do:** the end of each cycle in the log has a `Collection Timing Summary`, with the time each part took. Turn off the parts you do not need: the Windows checks are switched off on the account, and an empty list in the ESXi software packages file collects no packages, see [Configuration files](configuration-files.md#the-format). Check the summary again after one cycle.

## The Cloud Proxy cannot start the adapter

**What you see:** the account does not start, and the Cloud Proxy shows an error about the image.

**Cause:** the Cloud Proxy cannot pull the adapter's container image, from the public registry, or from your private registry on a dark site. See [How It Works](../installation-guide/how-it-works.md) and [Dark Site Installation](../installation-guide/dark-site.md).

**What to do:** check the Cloud Proxy's access to the registry. On a dark site, check the private registry and the image in it.

---

**Next:** [Configuration files](configuration-files.md) · [Log Messages](log-messages.md)
