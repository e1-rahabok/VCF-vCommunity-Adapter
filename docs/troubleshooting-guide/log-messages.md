# Log Messages

The messages the pack writes to its adapter log, what each one means, and what to do. The text is copied from the code: `<…>` stands for a name, a number or a reason from your environment. Look up the message by its first words.

Read [First Steps](first-steps.md#5-read-the-adapter-log) for how to get the log. Messages are grouped by what they tell you. Some messages are written at debug level, for the developers of the pack, and are not listed here.

**On this page:** [The whole cycle](#the-whole-cycle) · [Connection and certificate](#connection-and-certificate) · [Values from VCF Operations](#values-from-vcf-operations) · [Objects](#objects) · [Configuration](#configuration) · [Windows guests](#windows-guests)

---

## The whole cycle

| Message | Level | Meaning | What to do |
| :--- | :--- | :--- | :--- |
| `Finished total data collection.` | Info | The cycle completed. | Nothing. |
| `Finished <collector> collection successfully.` | Info | One collector completed. The collectors are cluster, host, VM, datastore, vCenter, vSphere World and Datacenter. | Nothing. |
| `Collection Timing Summary` | Info | Written at the end of each cycle, with the time each part took. | Use it to find a slow part. See [Symptoms](symptoms.md#collection-is-slow). |
| `Main data collection thread error in <collector>: <reason>` | Error | One collector failed. The others still ran and published. | Read the reason. Send it with the log when you ask for help. |
| `Unexpected collection error`, followed by a traceback | Error | The whole cycle failed. Nothing from this account was published. | Send the traceback when you ask for help. |
| `Unexpected connection test error: <reason>` | Error | Validate Connection failed. The reason follows. | See [Symptoms](symptoms.md#validate-connection-fails). |
| `Stats query <path> failed with HTTP <code>` | Warning | VCF Operations did not return the stats of part of the cycle. Resources in the failed request get no value. | Check the account's access to VCF Operations, and the state of VCF Operations. If it repeats, send the log. |
| `Properties query failed with HTTP <code>` | Warning | The same, for properties. | As above. |

## Connection and certificate

| Message | Level | Meaning | What to do |
| :--- | :--- | :--- | :--- |
| `No vCenter Adapter Instance found matching vCenter Server '<address>'` | Error, on the account | The vCenter address does not match the native vCenter Adapter Instance. Nothing is published. | See [Symptoms](symptoms.md#the-account-is-collecting-but-the-vcenter-has-no-vcommunity-values). |
| `Could not read the certificate of vCenter <host>:<port>, so it is not compared: <reason>` | Warning | The certificate could not be read this time. The check is skipped for this cycle. | Check the network between the Cloud Proxy and vCenter. |
| `vCenter <host>:<port> presented no certificate, so it is not compared.` | Warning | vCenter sent no certificate. | Check the address and port. |
| `vCenter TLS Validation is Trust on First Use: the certificate of vCenter is not checked before the user name and password are sent, ...` | Info | Written at each connection, in the default mode. It is information, not a warning, so the Collection Warnings alert does not fire for it. | Set `Pinned` or `Enabled` if the network is not fully trusted. See [TLS and Security Settings](../configuration-guide/tls-and-security.md). |
| `The vCenter certificate does not match the pinned thumbprint; the libraries were not read.` | Warning | `Pinned` refused the REST connection that reads the Content Libraries. Nothing was sent. The other data of the vCenter is published. | Compare the certificate with vCenter, as for a changed certificate. |
| `Could not read the recorded vCenter certificate, so it is not compared this time: <reason>` | Warning | The thumbprint recorded on the vCenter object could not be read. | Usually temporary. If it repeats, send the log. |
| `The certificate of vCenter <host> has changed: SHA-256 thumbprint <old> before, <new> now. Collection continues.` | Warning | The vCenter certificate is different from the one recorded. Both thumbprints are in the line. | See [Symptoms](symptoms.md#the-certificate-of-vcenter-changed). |

## Values from VCF Operations

| Message | Level | Meaning | What to do |
| :--- | :--- | :--- | :--- |
| `Failed to read VM Performance stats, so no VM or Guest OS Performance this cycle - <reason>` | Warning | The stats of all VMs could not be read. No VM or Guest OS KPI for the cycle. | Usually temporary. If it repeats, send the log with the reason. |
| `Failed to read ESXi Performance stats, so no ESXi Performance this cycle - <reason>` | Warning | The same, for the host KPI. | As above. |
| `Failed to read the network speeds, so no Network Speed Degradation this cycle - <reason>` | Warning | The network speeds could not be read. | As above. |
| `No NIC speeds for any host, so no Network Speed Degradation this cycle` | Warning | No host has a NIC speed. The usual cause is the policy. | See [Policy](../configuration-guide/policy.md). |
| `Failed to read Operational Availability, so none this cycle - <reason>` | Warning | The availability of the vCenter could not be read. | As above. |
| `No Operational Availability data for any host, so none is published this cycle` | Warning | No host has an availability value. | Check the vCenter adapter collects the hosts. |
| `Failed to read VM shares, so no Share per vCPU or per MB this cycle - <reason>` | Warning | The VM shares could not be read. | As above. |
| `Failed to read the usable capacity and memory tier stats of Cluster Consumption - <reason>` | Warning | Cluster Consumption has no capacity stats this cycle. | As above. |
| `Periodic Cluster Check: could not read which clusters are calculated. Trying next cycle.` | Warning | The timestamps of the Periodic Cluster Check could not be read. Nothing is calculated this cycle. | Usually temporary. |
| `Periodic Cluster Check: <N> of <M> clusters due for the … to <window end>.` | Info | How many clusters are calculated in this cycle, and for which window. | Nothing. |
| `Failed to read the Periodic Cluster Check - <reason>` | Warning | The check did not run this cycle. The clusters stay due and are tried again. | As above. |
| `Cluster Delta counts: could not read which clusters are calculated. Trying next cycle.` | Warning | The Cluster Delta counts were not calculated this cycle. | Usually temporary. |
| `Cluster Delta counts: <n> clusters could not be read. Trying next cycle.` | Warning | Some clusters could not be read, so the counts are not published to avoid a wrong count. | As above. If it repeats, send the log. |
| `Cluster Delta counts for the window to <window end>: <n> closed, <n> opened, of <n> clusters.` | Info | The counts of the window. | Nothing. |
| `Cluster Check Time '<text>' is not HH:MM. Using 00:00 UTC.` | Warning | The time on the account is not valid. The default is used. | Correct the setting. See [Adapter Instance](../configuration-guide/adapter-instance.md#2-advanced-settings-optional). |
| `Cluster Check Period '<text>' is not one of 01, 02, 04, 06, 08, 12, 24. Using 24 hours.` | Warning | The period on the account is not valid. The default is used. | Correct the setting. |
| `Cluster Check Worst Percent '<text>' is not a whole number from 0 to 50. Using 5.` | Warning | The worst percent on the account is not valid. The default is used. | Correct the setting. |
| `Stats query <path> failed with HTTP <code>: <n> resources have no stats this cycle` / `Properties query failed with HTTP <code>: <n> resources have no properties this cycle` | Warning | One batch of the VCF Operations read failed. Those resources have no value this cycle, and the totals built on them (for example a cluster or the vSphere World) are partial for this cycle. | Usually temporary. If it repeats, check VCF Operations itself. |
| `Failed to read <type> objects from the vCenter: <reason>. Nothing is published for them this cycle.` | Error | A vCenter read of one object type failed. It used to look like "no objects". Now it is an error, and the other object types still publish. | Read the reason. Usually a lost connection or an expired session: the next cycle retries. |

## Objects

These messages are about one object. The rest of the cycle is published.

| Message | Level | Meaning | What to do |
| :--- | :--- | :--- | :--- |
| `Failed to retrieve <what> for : <object> - <reason>` | Warning | One object did not get that value. For example, `Failed to retrieve vSphere Cluster Risk metrics for : <cluster>`. | The reason is at the end of the line. Often a value the object does not have. |
| `Skipping <collector> data collection on <object> due to error: <reason>` | Warning | One object was skipped for this cycle. Its other values were not published either. | Read the reason. If it repeats for one object, send the log. |
| `Skipping vCenter data collection on due to error: <reason>` | Warning | The vCenter object was skipped for this cycle. | As above. |
| `Failed to publish … on vSphere World - <reason>` | Warning | A summary value on the vSphere World object failed. The others were published. | As above. |
| `Failed to collect <object> data - <reason>` | Warning | A whole object type failed this cycle. The others were published. | As above. |

## Configuration

| Message | Level | Meaning | What to do |
| :--- | :--- | :--- | :--- |
| `Configuration file '<name>.xml' could not be read from VCF Operations (HTTP <code>). Nothing is collected from it.` | Warning | The file is not there, or could not be read. The same text is the event on the vCenter object. | See [Configuration files](configuration-files.md). |
| `Configuration file '<name>.xml' is not valid XML (<reason>). Nothing is collected from it until it is corrected.` | Error | The file has an XML error. The reason is the parser's. The same text is the event on the vCenter object. | See [Configuration files](configuration-files.md). |
| `Configuration file '<name>.xml' could not be read from VCF Operations (<reason>). Nothing is collected from it this cycle.` | Error | The read of the file raised an error, such as a lost connection to VCF Operations. The other files are still read. | Usually temporary. The next cycle reads it again. |
| `Windows Service names left out because they contain characters that are not allowed (letters, digits, space and _ . $ # @ ( ) + - only): <names>` | Warning | Some service names have characters the pack does not accept. The others are checked. | See [Symptoms](symptoms.md#windows-service-names-are-left-out). |

## Windows guests

| Message | Level | Meaning | What to do |
| :--- | :--- | :--- | :--- |
| `Command execution failed on <vm>` | Error | The PowerShell script did not start in the guest. The caller then logs the reason for the object. | Check VMware Tools and the Windows credential. See [Symptoms](symptoms.md#windows-properties-services-or-events-are-missing). |
| `File transfer failed to <vm>: <status> - <reason>` | Error | The script could not be copied into the guest. | Check the credential, VMware Tools, and the guest file transfer TLS setting. |
| `File transfer failed. Skipping Windows Event Log reading on <vm>` | Info | The script was not copied, so the event logs of this VM are skipped. | As above. |
| `Failed to create temporary directory on <vm>: <reason>` | Error | The guest could not create the folder for its output. | Check the rights of the Windows credential in the guest. |
| `Can not download powershell output from <vm>. Expected file is: <path>` | Error | The script ran, but its output file was not found. | Check that the guest can write to its temporary folder. |
| `Cannot find the Windows Service CSV file on <vm>` | Error | The script did not write its service list. | As above. |
| `Cannot find the Windows Operating System information CSV file on <vm>` | Error | The script did not write its OS information. | As above. |
| `Cannot find the Windows Event Log XML file on <vm>` | Error | The script did not write its event log output. | As above. |
| `CSV parsing error on <vm>: <reason>` | Error | The output of the script could not be read. | Send the log with the reason. |
| `An error occurred during Windows Event Log collection: <reason>` | Error | The event logs of this VM failed. The other data of the VM is published. | Send the log with the reason. |
| `Can not find Windows Event details on <vm>` | Info | The script ran and found no events. | Nothing. |
| `Sending Windows Event details for <vm>` | Info | Events were found and sent to VCF Operations. | Nothing. |
| `Failed to write file. HTTP status: <code> on <vm>` | Error | The script could not be copied into the guest. | As for `File transfer failed`. |
| `Failed to retrieve Guest OS Performance metrics for : <vm> - <reason>` | Warning | The Guest OS KPI of one VM failed. | Read the reason. |
| `The PowerShell step on <vm> did not finish in 300 seconds, so it was stopped.` | Warning | A script in the guest hung, so it was stopped, and the guest data of this VM is skipped for this cycle. Other VMs are not affected. | Check the VM for a hung service or a blocked PowerShell session. If it repeats, the VM is the cause. |
| `Windows Service monitoring skipped for <vm>: ...` / `Windows Event Log reading skipped for <vm>: ...` / `Windows OS information skipped for <vm>: ...` | Warning | The step was stopped by the timeout above. | As above. |
| `The guest time budget of 30 minutes for this collection is spent. Windows guest monitoring is skipped for the remaining VMs until the next cycle.` | Warning | The guest work of this cycle took longer than its budget. The VMs after this point are not read this cycle. | Reduce the Windows guests, or the event and service lists. The next cycle starts again from the first VM. |
| `Windows Service monitoring failed on <vm>: <reason>` / `Windows OS information failed on <vm>: <reason>` | Error | A step failed for one VM. The other VMs go on. | Read the reason. |
| `<vm> has <n> Windows events. Only the first 100 are sent this cycle.` | Warning | More events were in the event list than one cycle sends for a VM. | Narrow the event list in the configuration file. |
| `The Windows Service CSV on <vm> has no Name, DisplayName, Status, StartType column.` / `The Windows Operating System CSV on <vm> has no ...` / `The Windows Event CSV on <vm> has no Level or Event column.` | Error | The script's output does not have the expected columns. | Check the script is the one in this version of the pack. |

---

**Next:** [First Steps](first-steps.md) · [Symptoms](symptoms.md) · [Configuration files](configuration-files.md)
