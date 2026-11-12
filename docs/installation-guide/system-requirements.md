# System Requirements

## Platform

- VCF Operations 8.18 or later.
- vCenter Server 8 or later, including VCF 9.x.
- A VCF Operations Cloud Proxy that can reach the vCenter Server.
- HTTPS access from every Cloud Proxy that runs the pack to the container registry `ghcr.io`. Without it, use a private registry: see [Dark Site Installation](dark-site.md).

### vSphere API version

The adapter uses the vSphere 8.0 Update 3 API, also against vCenter 9.x. It calls vCenter through pyVmomi 8.0.3.0.1, pinned in `Management Pack/adapter_requirements.txt`. The vSphere API is backward compatible: the adapter asks for the newest API version it knows, and vCenter 9.x answers in that version. Everything the adapter collects therefore works with VCF 9.x, but properties and object types that are new in the vSphere 9 API are not visible to the adapter until it moves to pyVmomi 9.x.

## Container registry

The Cloud Proxy runs the adapter as a container. It pulls the image the first time you install the `.pak` file, and again after every upgrade. The image is named in `vCommunity.conf` inside the `.pak` file and is pulled by digest from:

```
ghcr.io/e1-rahabok/vcf-operations-vcommunity
```

Keep registry access open if you want to upgrade without extra steps. If the Cloud Proxy needs an internet proxy, you can set one when you deploy the Cloud Proxy OVF.

In a regulated environment, consider a private registry even when internet access is possible: see [TLS and Security Settings](../configuration-guide/tls-and-security.md#container-registry).

## User Account Requirements

### vCenter Server

- An account with the **Read-only** role, assigned with **Propagate to children** selected.
- The `Host.Configuration.ImageConfiguration` privilege, to read ESXi software packages (VIBs) and the ESXi install date.
- For Windows monitoring only: the **Virtual machine** > **Guest operations** privileges (guest operation modifications, program execution and queries). The pack creates a temporary folder in the guest, copies a script into it, runs it, reads the output back and deletes the folder, and vSphere checks these privileges on the vCenter account for each of those calls. The Read-only role does not include them.

### Guest OS (Windows), optional

This account is needed only if **Guest OS Service Monitoring Status** or **Windows Event Log Monitoring Status** is `Enabled` (see [Adapter Instance](../configuration-guide/adapter-instance.md#2-advanced-settings-optional)). The checks run through VMware Tools, as this Windows account.

- A standard domain or local Windows account is enough. A standard user can read service status (`Get-Service`) and OS information (WMI `Win32_OperatingSystem` and an `HKLM` registry read) by default.
- For Windows Event Log monitoring, add the account to the local **Event Log Readers** group. A standard user can read the `Application`, `Setup` and `System` logs, but not `Security`. **Event Log Readers** grants read access to all of them without administrator rights.
- Don't use a local Administrator account.
- [TLS and Security Settings](../configuration-guide/tls-and-security.md#what-runs-inside-a-windows-vm) describes what runs in the VM and how the file transfer is checked.

---

**Next:** [Installation](installation.md)
