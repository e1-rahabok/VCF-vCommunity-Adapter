# Log Messages

The messages the pack writes to `adapter.log`, what each one means, and what to do about it. The text is copied from the code. `<…>` stands for a name, a number or a reason from your environment. Look a message up by its first words. [First Steps](first-steps.md#5-read-the-adapter-log) shows how to get the log.

Every warning and error in a cycle is also counted in `vCommunity|Collection Health|Warnings in Last Cycle` on the vCenter object, and the first one is kept in `vCommunity|Collection Health|First Warning`. Debug messages, which are meant for developers, are not listed.

[The whole cycle](#the-whole-cycle) · [Connection and certificate](#connection-and-certificate) · [Values from VCF Operations and vCenter](#values-from-vcf-operations-and-vcenter) · [Objects](#objects) · [Content libraries and Business Applications](#content-libraries-and-business-applications) · [Configuration](#configuration) · [Windows guests](#windows-guests)

---

## The whole cycle

Each cycle runs these collection jobs in parallel: `collect_cluster_data`, `collect_host_data`, `collect_vm_data`, `collect_datastore_data`, `collect_vcenter_data`, `collect_world_data`, `collect_datacenter_data`, `collect_content_libraries` and `collect_business_applications`.

| Message | Level | Meaning | What to do |
| :--- | :--- | :--- | :--- |
| `Finished total data collection.` | Info | The cycle completed. | Nothing. |
| `Finished <job> collection successfully.` | Info | One job completed. | Nothing. |
| `Collection Timing Summary`, followed by `Collection Operation: <job> > Duration: <time>` lines | Info | Written at the end of each cycle, with the time of each job. | Use it to find the slow part. See [Symptoms](symptoms.md#collection-is-slow). |
| `Main data collection thread error in <job>: <reason>` | Error | One job failed. The others still ran and published. | Read the reason, and include it when you ask for help. |
| `Unexpected collection error`, followed by a traceback | Error | The cycle stopped. The account also shows the error. | Include the traceback when you ask for help. |
| `Unexpected connection test error`, followed by a traceback | Error | Validate Connection failed. The Validate Connection message has the reason. | See [Symptoms](symptoms.md#validate-connection-fails). |

## Connection and certificate

| Message | Level | Meaning | What to do |
| :--- | :--- | :--- | :--- |
| `No vCenter Adapter Instance found matching vCenter Server '<address>'` | Error, shown on the account | The vCenter address does not match the native vCenter Adapter Instance. Nothing is published. | See [Symptoms](symptoms.md#the-account-is-collecting-but-the-vcenter-has-no-vcommunity-values). |
| `vCenter TLS Validation is Trust on First Use: the certificate of vCenter is not checked before the user name and password are sent, ...` | Info | Written at each connection in the default mode. It is information, so it does not count as a warning. | Set `Pinned` or `Enabled` if the network is not fully trusted. See [TLS and Security Settings](../configuration-guide/tls-and-security.md). |
| `Recorded the certificate of vCenter <host>: SHA-256 thumbprint <thumbprint>.` | Info | The first collection recorded the vCenter certificate. | Nothing. |
| `The certificate of vCenter <host> has changed: SHA-256 thumbprint <old> before, <new> now. Collection continues. ...` | Warning | vCenter presents a different certificate from the recorded one. | See [Symptoms](symptoms.md#the-certificate-of-vcenter-changed). |
| `Could not read the certificate of vCenter <host>:<port>, so it is not compared: <reason>` | Warning | The certificate could not be read this cycle, so the comparison is skipped. | Check the network between the Cloud Proxy and vCenter. |
| `vCenter <host>:<port> presented no certificate, so it is not compared.` | Warning | vCenter sent no certificate. | Check the address and port. |
| `Could not read the recorded vCenter certificate, so it is not compared this time: <reason>` | Warning | The thumbprint recorded on the vCenter object could not be read from VCF Operations. | Usually temporary. If it repeats, send the log. |
| `The vCenter certificate does not match the pinned thumbprint; the libraries were not read.` | Warning | With `Pinned`, the REST login that reads the content libraries was refused, and nothing was sent. The rest of the vCenter data is published. | Check the certificate in vCenter, as for a changed certificate. |
| `Guest file transfer TLS validation is Disabled: the ESXi certificate is not checked.` | Info | **Guest File Transfer TLS Validation** is `Disabled`. | Nothing, if that is intended. See [TLS and Security Settings](../configuration-guide/tls-and-security.md#guest-file-transfer-tls-validation). |

## Values from VCF Operations and vCenter

These messages mean that one input could not be read. The values built on it are missing for the cycle.

| Message | Level | Meaning | What to do |
| :--- | :--- | :--- | :--- |
| `Stats query <path> failed with HTTP <code>: <n> resources have no stats this cycle` | Warning | One batch of a stats read failed. Those objects get no value this cycle, and the totals built on them, such as a cluster or vSphere World value, are partial. | Usually temporary. If it repeats, check VCF Operations itself. |
| `Properties query failed with HTTP <code>: <n> resources have no properties this cycle` | Warning | The same, for properties. | As above. |
| `Stats query <path> failed with HTTP <code>` | Warning | A read of when values were last published failed. The step that needed it waits for the next cycle. | As above. |
| `Failed to read <type> objects from the vCenter: <reason>. Nothing is published for them this cycle.` | Error | The vCenter read of one object type failed. The other object types still publish. | Read the reason. Usually a lost connection or an expired session, and the next cycle retries. |
| `Invalid property requested for <type>: <path>. Nothing is published for it this cycle.` | Error | vSphere does not know a property path. For VMs, this is usually a wrong entry in the VM Options file, and no VM is read this cycle. | See [Symptoms](symptoms.md#no-vm-values-after-a-change-to-the-vm-options-file). |
| `Could not release the container view of <type>: <reason>` | Warning | A vCenter read finished, but its view was not closed. The data was read. | Nothing, unless it repeats. |
| `Failed to read VM Performance stats, so no VM or Guest OS Performance this cycle - <reason>` | Warning | The stats of the VMs could not be read. No VM or Guest OS KPI this cycle. | Usually temporary. If it repeats, send the log with the reason. |
| `Failed to read ESXi Performance stats, so no ESXi Performance this cycle - <reason>` | Warning | The same, for the host KPI. | As above. |
| `Failed to read the network speeds, so no Network Speed Degradation this cycle - <reason>` | Warning | The NIC speeds could not be read. | As above. |
| `No NIC speeds for any host, so no Network Speed Degradation this cycle` | Warning | No host has a NIC speed. The usual cause is the policy. | See [Policy](../configuration-guide/policy.md). |
| `Failed to read Operational Availability, so none this cycle - <reason>` | Warning | The availability inputs could not be read. | As above. |
| `No Operational Availability data for any host, so none is published this cycle` | Warning | No host has an availability value. | Check that the vCenter adapter collects the hosts. |
| `Failed to read VM shares, so no Share per vCPU or per MB this cycle - <reason>` | Warning | The VM shares could not be read. | Usually temporary. |
| `Failed to read the clusters from VCF Operations, so no Cluster Consumption - <reason>` | Warning | The cluster list for Cluster Consumption could not be read. | Usually temporary. |
| `Failed to read the usable capacity and memory tier stats of Cluster Consumption - <reason>` | Warning | Cluster Consumption has no capacity stats this cycle. | Usually temporary. |
| `Failed to read the resource pools, so no Number of Resource Pools this cycle - <reason>` | Warning | The resource pools could not be read. | Usually temporary. |
| `Failed to count the port groups of this vCenter, so Number of Port Groups is not updated - <reason>` | Warning | The port group count on the vCenter object keeps its last value. | Usually temporary. |
| `Failed to fetch global license assignment data: <reason>` | Warning | The license assignments could not be read from vCenter, so the hosts get no license properties this cycle. | Usually temporary. If it repeats, send the log. |
| `Periodic Cluster Check: <n> of <m> clusters due for the <hours> hours to <window end>, worst <percent> %.` | Info | How many clusters are calculated in this cycle, and for which window. | Nothing. |
| `Periodic Cluster Check: Close for Business set on <n> of <m> due clusters for the <hours> hours to <window end>.` | Info | The result of this cycle. | Nothing. |
| `Periodic Cluster Check of <cluster>: no Close for Business for the window to <window end> - samples in the window: <counts>` | Info | The cluster had too little KPI data in the window. | Nothing, unless it repeats for the same cluster. |
| `Periodic Cluster Check: could not read which clusters are calculated. Trying next cycle.` | Warning | Nothing is calculated this cycle. | Usually temporary. |
| `Failed to read the Periodic Cluster Check - <reason>` | Warning | The check did not run this cycle. The clusters stay due and are tried again. | Usually temporary. |
| `Cluster Delta counts: could not read when they were last published. Trying next cycle.` | Warning | The Cluster Delta counts are not calculated this cycle. | Usually temporary. |
| `Cluster Delta counts: could not read which clusters are calculated. Trying next cycle.` | Warning | As above. | Usually temporary. |
| `Cluster Delta counts: <n> clusters could not be read. Trying next cycle.` | Warning | Some clusters could not be read, so the counts are held back rather than published wrong. | If it repeats, send the log. |
| `Cluster Delta counts for the window to <window end>: <n> closed, <n> opened, of <n> clusters.` | Info | The counts of the window. | Nothing. |

## Objects

These messages are about one object. The rest of the cycle is published.

| Message | Level | Meaning | What to do |
| :--- | :--- | :--- | :--- |
| `Failed to retrieve <what> for : <object> - <reason>` | Warning | One object did not get that value, for example `Failed to retrieve vSphere Cluster Risk metrics for : <cluster>`. | The reason is at the end of the line. Often the object does not have the value. |
| `Failed to calculate vSphere Cluster Consumption metrics for : <cluster> - <reason>` | Warning | The same, for Cluster Consumption. | As above. |
| `Failed to publish <what> for : <object> - <reason>` | Warning | A value was calculated but could not be added, for example the VM Guest OS KPI or the VM shares. | Send the log if it repeats. |
| `<KPI> for <cluster>: no data, so left out: <sub-metrics>` | Info | These sub-metrics had no data and were left out of the KPI, for example `Cluster Risk for <cluster>: …`. | Nothing. See [Missing data](../concepts/kpi-scoring-models.md#missing-data). |
| `Skipping <type> data collection on <object> due to error: <reason>` | Warning | One cluster, host (`ESX`), VM or datastore was skipped this cycle, with all its values. | Read the reason. If it repeats for one object, send the log. |
| `Skipping vCenter data collection on due to error: <reason>` | Warning | The vCenter object was skipped this cycle. | As above. |
| `Failed to collect vSphere World data - <reason>` / `Failed to collect Datacenter data - <reason>` | Warning | The vSphere World or Datacenter values failed this cycle. | As above. |
| `Failed to publish <what> on vSphere World - <reason>` | Warning | One summary value on vSphere World failed. The others were published. | As above. |
| `Regex parsing failed for guestDetailedData: <reason>` | Warning | The detailed guest OS data of a VM could not be parsed. Its other properties are published. | Nothing, unless it repeats. |

## Content libraries and Business Applications

| Message | Level | Meaning | What to do |
| :--- | :--- | :--- | :--- |
| `Content library collection failed - <reason>` | Warning | The content libraries were not read this cycle, so the Content Library and Library Item objects get no new values. | Read the reason. If it repeats, send the log. |
| `Business Application performance failed - <reason>` | Warning | The Business Application values were not calculated this cycle. Any failed read stops the whole calculation, so no Tier, Business Application or Enterprise gets a value. | Usually temporary. If it repeats, send the log. |

## Configuration

| Message | Level | Meaning | What to do |
| :--- | :--- | :--- | :--- |
| `Configuration file '<name>.xml' could not be read from VCF Operations (HTTP <code>). Nothing is collected from it. ...` | Warning | VCF Operations has no file with that name. The same text is the event on the vCenter object. | See [Configuration Files](configuration-files.md). |
| `Configuration file '<name>.xml' could not be read from VCF Operations (<reason>). Nothing is collected from it this cycle.` | Error | The read of the file failed, for example because the connection dropped. The other files are still read. | Usually temporary. The next cycle reads it again. |
| `Configuration file '<name>.xml' is not valid XML (<reason>). Nothing is collected from it until it is corrected.` | Error | The file has an XML error. The reason is the parser's. The same text is the event on the vCenter object. | See [Configuration Files](configuration-files.md). |
| `Windows Service names left out because they contain characters that are not allowed (letters, digits, space and _ . $ # @ ( ) + - only): <names>. ...` | Warning | Some service names have characters the pack does not accept. The others are checked. | See [Symptoms](symptoms.md#windows-service-names-are-left-out). |
| `Cluster Check Time '<text>' is not HH:MM. Using 00:00 UTC.` | Warning | The time on the account is not valid, so the default is used. | Correct the setting. See [Adapter Instance](../configuration-guide/adapter-instance.md#2-advanced-settings-optional). |
| `Cluster Check Period '<text>' is not one of 01, 02, 04, 06, 08, 12, 24. Using 24 hours.` | Warning | The period on the account is not valid. | Correct the setting. |
| `Cluster Check Worst Percent '<text>' is not a whole number from 0 to 50. Using 5.` | Warning | The worst percent on the account is not valid. | Correct the setting. |
| `Monster VM CPU (% of host cores) '<text>' is not a whole number from 1 to 100. Using 50.` | Warning | The Monster VM setting is not valid. The same message exists for the other two Monster VM settings. An empty setting uses the default with no warning. | Correct the setting. |

## Windows guests

These appear only when Windows Service or Windows Event Log monitoring is enabled. A failure on one VM does not affect the others.

| Message | Level | Meaning | What to do |
| :--- | :--- | :--- | :--- |
| `Skipping <vm> is not a Windows Guest.` | Info | The VM is not a Windows guest, or its VMware Tools are not running. | Nothing, unless the VM is Windows. Then check VMware Tools. |
| `Exception during file transfer to <vm>: <reason>` | Error | The script could not be copied into the guest. When the reason starts with `The certificate of the ESXi host does not match`, the host certificate was refused and nothing was sent. | Check the Windows credential, VMware Tools and **Guest File Transfer TLS Validation**. See [Symptoms](symptoms.md#windows-properties-services-or-events-are-missing). |
| `File transfer failed to <vm>: <status> - <reason>` | Error | The ESXi host answered the file transfer with an error status. | Check the Windows credential and VMware Tools. |
| `Cannot find the Windows Service CSV file on <vm>` / `Cannot find the Windows Operating System information CSV file on <vm>` | Error | The script was not copied into the guest, so the step stopped. The line before it gives the reason. | As for the transfer messages above. |
| `File transfer failed. Skipping Windows Event Log reading on <vm>` | Info | The event log script was not copied, so the event logs of this VM are skipped. | As above. |
| `Exception during file creation on <vm>: <reason>` / `Failed to write file. HTTP status: <code> on <vm>` | Error | The XML file with the Event IDs could not be written into the guest. | As above. |
| `Cannot write the Windows Event Log XML file on <vm>` / `Cannot find the Windows Event Log XML file on <vm>` | Error | The event log step stopped because its XML file is missing in the guest. | As above. |
| `There was an error during file check. <reason>` | Error | The guest's file list could not be read. | Check VMware Tools. |
| `<reason> Guest file transfers to this host go ahead without checking its certificate. Set 'Guest File Transfer TLS Validation' to Strict to skip such VMs instead.` | Warning | With `Pinned`, vCenter has no thumbprint for this ESXi host, so its certificate is not checked. Written once per host. | Reconnect the host in vCenter to record its thumbprint, or set `Strict`. |
| `Can not download powershell output from <vm>. Expected file is: <path>` | Error | The script ran, but its output file was not found. | Check that the guest can write to its temporary folder. |
| `No Windows Service details were read from <vm>.` / `No Windows Operating System information was read from <vm>.` / `No Windows Event details were read from <vm>.` | Error | Follows the line above: the step published nothing. | As above. |
| `CSV parsing error on <vm>: <reason>` | Error | The script's output could not be read. | Send the log with the reason. |
| `The Windows Service CSV on <vm> has no Name, DisplayName, Status, StartType column.` / `The Windows Operating System CSV on <vm> has no ... column.` / `The Windows Event CSV on <vm> has no Level or Event column.` | Error | The script's output does not have the expected columns. | Check that the script is the one from this version of the pack. |
| `Skipping a Windows Service row with <n> fields, expected <m>.` | Warning | One row of the service output was malformed and left out. | Nothing, unless it repeats. |
| `Can not find Windows Service details on <vm>` / `Can not find Windows Operating System informations on <vm>` / `Can not find Windows Event details on <vm>` | Info | The script ran and found nothing to report. | Nothing. |
| `<vm> has <n> Windows events. Only the first 100 are sent this cycle.` | Warning | More events matched than one cycle sends for a VM. | Narrow the Event IDs in the configuration file. |
| `Windows Service monitoring skipped for <vm>: The PowerShell step on <vm> did not finish in 300 seconds, so it was stopped.` | Warning | A script hung in the guest and was stopped. The guest data of this VM is skipped this cycle. The same text exists for `Windows Event Log reading skipped` and `Windows OS information skipped`. | Check the VM for a hung service or a blocked PowerShell session. If it repeats, the VM is the cause. |
| `Could not stop process <pid> on <vm>: <reason>` | Warning | A hung script could not be stopped. | Check the VM. |
| `Process <pid> on <vm> is no longer listed, and its exit code is unknown.` | Warning | The script ended, but its exit code could not be read. The output is still read. | Nothing, unless output is missing. |
| `The guest time budget of 30 minutes for this collection is spent. Windows guest monitoring is skipped for the remaining VMs until the next cycle.` | Warning | The guest work of this cycle used its time limit. | Reduce the number of Windows guests or the length of the lists. The next cycle starts again from the first VM. |
| `Windows Service monitoring failed on <vm>: <reason>` / `Windows OS information failed on <vm>: <reason>` / `An error occurred during Windows Event Log collection on <vm>: <reason>` | Error | One step failed for one VM. `Command execution failed on <vm>` as the reason means the script did not start. | Read the reason. Check VMware Tools and the Windows credential. |
| `Could not delete the temporary folder <folder> on <vm>: <reason>` | Warning | The folder under `C:\Windows\Temp` stays in the guest. | Delete it by hand if needed. |

---

**Next:** [First Steps](first-steps.md) · [Symptoms](symptoms.md) · [Configuration Files](configuration-files.md)
