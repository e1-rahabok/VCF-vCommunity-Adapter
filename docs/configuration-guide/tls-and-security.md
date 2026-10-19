# TLS and Security Settings

The pack connects to vCenter with a service account. With Windows monitoring on, it also runs a PowerShell script inside Windows VMs. This page lists what the pack checks on those connections, what it runs, and what to set in a regulated environment.

**On this page:**

- [Settings](#settings)
- [vCenter TLS Validation](#vcenter-tls-validation)
- [Guest File Transfer TLS Validation](#guest-file-transfer-tls-validation)
- [What runs inside a Windows VM](#what-runs-inside-a-windows-vm)
- [Container registry](#container-registry)
- [Accounts](#accounts)
- [Upgrading from an earlier version](#upgrading-from-an-earlier-version)
- [Reporting a vulnerability](#reporting-a-vulnerability)

---

## Settings

All three are under **Advanced Settings** of the [Adapter Instance](adapter-instance.md#2-advanced-settings-optional).

| Setting | Default | What it does |
| :--- | :--- | :--- |
| **vCenter TLS Validation** | `Enabled` | How the vCenter certificate is checked: `Enabled`, `Pinned` or `Disabled`. |
| **vCenter Thumbprint (SHA-256)** | *(empty)* | The certificate thumbprint to accept. Used only when vCenter TLS Validation is `Pinned`. |
| **Guest File Transfer TLS Validation** | `Pinned` | How the ESXi host certificate is checked when a script is sent to a Windows VM: `Pinned` or `Disabled`. Used only when Windows monitoring is enabled. |

`Disabled` exists for labs. It writes a warning to the adapter log on every collection.

---

## vCenter TLS Validation

The adapter sends the vCenter service account name and password to vCenter. The check on the vCenter certificate decides whether anything else on the network path can read them.

| Mode | The adapter accepts the vCenter when... | Use it for |
| :--- | :--- | :--- |
| `Enabled` | The certificate chain and the host name are valid for the trust store of the adapter container. | A vCenter with a certificate from a CA that the container trusts. |
| `Pinned` | The certificate matches the thumbprint in **vCenter Thumbprint (SHA-256)**. The chain is not checked: the thumbprint is the identity. | A vCenter with a self-signed certificate, or one from an internal CA that the container does not trust. |
| `Disabled` | Always. Nothing is checked. | A lab. Never production. |

A wrong or incomplete setting is refused, never treated as `Disabled`: `Pinned` without a thumbprint, a thumbprint that is not a SHA-256 or SHA-512 value, and an unknown mode all stop the connection. A SHA-1 thumbprint is not accepted.

When the thumbprint does not match, the connection stops before the vCenter user name and password are sent. **Validate Connection** and the adapter log show the thumbprint that the vCenter presented. Compare it with the certificate in vCenter before you change the setting. A thumbprint copied from the failing connection proves nothing about who answered.

### Get the thumbprint

From a machine you trust, with OpenSSL:

```bash
openssl s_client -connect vcenter.example.com:443 -servername vcenter.example.com </dev/null 2>/dev/null \
  | openssl x509 -noout -fingerprint -sha256
```

The output is `sha256 Fingerprint=AB:CD:...`. Paste the part after `=`. Capitals, small letters and `:` between the bytes are all accepted.

This reads the certificate over the network, so check the value against a second source before you rely on it: your certificate inventory, or the certificate details in the management interface of the vCenter itself.

When the vCenter certificate is replaced, the thumbprint changes, and the Adapter Instance has to be updated. With `Enabled` it does not.

---

## Guest File Transfer TLS Validation

To read Windows Services, OS information and Event Logs, the pack sends a script to the VM and reads its output back. vCenter returns the address of the ESXi host that runs the VM for this transfer. An ESXi certificate is usually signed by a CA that the adapter container does not trust, so the chain cannot be checked.

| Mode | The transfer is made when... |
| :--- | :--- |
| `Pinned` | The ESXi host certificate matches the SSL thumbprint that vCenter records for that host. Nothing to enter: vCenter was already checked by the setting above. |
| `Disabled` | Always. Nothing is checked. |

In `Pinned` mode the transfer is refused when:

- the host presents a different certificate, or
- vCenter has no thumbprint for the host, or
- the host of the VM cannot be found.

The certificate is compared before anything is sent, so the script and its output are not exposed to a host that cannot prove it is the right one. The VM is skipped, and the reason is in the adapter log. The thumbprint of each host is read from vCenter once per collection.

This also means that after you replace an ESXi certificate, vCenter must have the new thumbprint (for a host that is connected normally it does) before Windows monitoring of its VMs continues.

---

## What runs inside a Windows VM

Only when **Guest OS Service Monitoring Status** or **Windows Event Log Monitoring Status** is `Enabled`. Both are `Disabled` by default.

For every Windows VM whose VMware Tools are running, through the vSphere GuestAPI and the Windows account in the credential:

1. A temporary folder is created under `C:\Windows\Temp`.
2. A PowerShell script that ships inside the pack is copied into it. For Event Logs, an XML file with your Event IDs is copied too.
3. `powershell.exe` runs the script. It reads service status, OS information, or the Event Log IDs you listed.
4. The output file is read back.
5. The folder is deleted. If that fails, the folder stays in the VM.

What this means for a review:

- It is a remote execution path: one credential, held in VCF Operations, can run PowerShell in every VM that the pack monitors. The scripts are fixed. They are not taken from a configuration file.
- The Windows Service names in the configuration file are put in the PowerShell command line. A name is accepted only if it contains letters, digits, space and `_ . $ # @ ( ) + -`, and starts with a letter, digit or `_`. Names with quotes, `;`, `|`, `&`, wildcards or new lines are left out, and one warning in the adapter log names them. So a user who can edit the configuration file cannot make the pack run their own commands in the VMs.
- Event IDs are sent as an XML file and read as data. They are not part of a command line.
- The account needs no administrator rights. See [User Account Requirements](../installation-guide/system-requirements.md#user-account-requirements). Do not use a local Administrator account.

Windows monitoring adds load to VCF Operations and to the VMs. See [the note on Guest OS monitoring](adapter-instance.md#2-advanced-settings-optional).

---

## Container registry

The Cloud Proxy pulls the adapter image from `ghcr.io`. In a regulated environment, use a private registry instead of opening `ghcr.io` for every Cloud Proxy: see [Dark Site Installation](../installation-guide/dark-site.md). The image is then pulled once, scanned and approved by you, and the Cloud Proxy has no standing dependency on a third-party registry.

---

## Accounts

- Use one vCenter service account for the pack, with read-only permission and nothing else it does not need. Do not reuse an account that other tools use. See [User Account Requirements](../installation-guide/system-requirements.md#user-account-requirements).
- Use a different Windows account for guest monitoring, and only when you enable it.
- Leave `esxi_packages.xml` and the Windows configuration files empty until you need them.

---

## Upgrading from an earlier version

Earlier versions did not check the vCenter certificate at all and had no setting for it. Now an Adapter Instance without the setting uses `Enabled`.

- A vCenter with a certificate that the container trusts keeps working.
- A vCenter with a self-signed or internal CA certificate stops connecting after the upgrade. **Validate Connection** says the certificate is not trusted. Set **vCenter TLS Validation** to `Pinned` and enter the thumbprint. Use `Disabled` only in a lab.
- Guest file transfers use `Pinned` without any change, because the thumbprints come from vCenter. If a VM is skipped, the adapter log says why.
- For many Adapter Instances, the [Bulk Adapter Instance Importer](../../tools/importer/importer.md) has columns for these settings.

---

## Reporting a vulnerability

Do not open a public issue. See [SECURITY.md](../../SECURITY.md).

---

**Next:** [Customization](customization.md)
