# TLS and Security Settings

The pack connects to vCenter with a service account. With Windows monitoring on, it also runs a PowerShell script inside Windows VMs. This page explains how the pack treats the certificates on those connections, what it runs, and what to set when a customer wants stricter checks.

**On this page:**

- [The approach](#the-approach)
- [Settings](#settings)
- [vCenter TLS Validation](#vcenter-tls-validation)
- [Guest File Transfer TLS Validation](#guest-file-transfer-tls-validation)
- [What runs inside a Windows VM](#what-runs-inside-a-windows-vm)
- [Container registry](#container-registry)
- [Accounts](#accounts)
- [Design considerations](#design-considerations)
- [Reporting a vulnerability](#reporting-a-vulnerability)

---

## The approach

**By default, the pack never stops collecting because of a certificate.** Many vCenter and ESXi certificates in the field are signed by the VMCA, or self-signed, and the Cloud Proxy does not trust them. Securing them is the customer's responsibility, not the adapter's. So the defaults watch the certificates instead of refusing them:

- **vCenter:** the pack records the vCenter certificate the first time, and reports on the vCenter object when it changes. Collection goes on.
- **ESXi, for Windows monitoring:** the pack checks each host's certificate against the thumbprint that vCenter already records for it. When vCenter has none, the transfer goes ahead and the adapter log says so.

A customer who wants a failed check to **stop** the connection can choose a stricter mode per Adapter Instance. Nothing changes until they do.

---

## Settings

All three are under **Advanced Settings** of the [Adapter Instance](adapter-instance.md#2-advanced-settings-optional): **Administration → Integrations → Accounts → VCF vCommunity Adapter →** your instance **→ ⋮ → Edit → Advanced Settings**.

| Setting | Default | Modes |
| :--- | :--- | :--- |
| **vCenter TLS Validation** | `Trust on First Use` | `Trust on First Use`, `Enabled`, `Pinned` |
| **vCenter Thumbprint (SHA-256)** | *(empty)* | Used only by `Pinned`. |
| **Guest File Transfer TLS Validation** | `Pinned` | `Pinned`, `Strict`, `Disabled`. Used only when Windows monitoring is enabled. |

An Adapter Instance created before these settings existed has them empty, which means the default: it keeps connecting as before.

---

## vCenter TLS Validation

| Mode | What the adapter does | When the check fails |
| :--- | :--- | :--- |
| `Trust on First Use` (default) | Connects whatever the certificate. Every collection, it compares the certificate's SHA-256 thumbprint with the one it recorded on the vCenter object. | It **reports** a change and keeps collecting. |
| `Enabled` | Checks the certificate chain and the host name against the trust store of the Cloud Proxy. | It **does not connect**. |
| `Pinned` | Compares the certificate with **vCenter Thumbprint (SHA-256)**, before the user name and password are sent. | It **does not connect**. |

### Trust on First Use

This is how the VCF Operations vCenter account itself works: you accept the certificate when you add the vCenter. The pack does the same, and then keeps watching it.

> **Warning.** The user name and password are sent before the certificate is checked. On the first connection, a server that impersonates vCenter receives them. Use `Pinned` or `Enabled` on any network you do not fully trust. The default is kept for the common lab and internal case, and the adapter log notes it at each connection.

The result is on the **vCenter** object in VCF Operations, under **vCommunity → Certificate**:

| Property | Meaning |
| :--- | :--- |
| **SHA-256 Thumbprint** | The thumbprint of the certificate vCenter presents now. The same value as `openssl x509 -noout -fingerprint -sha256`, in lower case and without colons. |
| **Status** | `Recorded`: the first collection, the certificate is now recorded. `Unchanged`: the same certificate as before. `Changed`: a different certificate, within the last 24 hours. `Unknown`: the certificate could not be read this collection, so nothing was compared. |
| **Previous SHA-256 Thumbprint** | The thumbprint before the last change. |
| **Last Changed** | When the last change was seen, in UTC. |

**When Status is `Changed`:**

- After a planned certificate replacement, it is expected. It returns to `Unchanged` after 24 hours.
- If nobody replaced the certificate, compare the new thumbprint with the certificate in vCenter. If they differ, another server answered as the vCenter and received the service account password: change the password, and find out why.

To be alerted, create a symptom on the vCenter property **vCommunity|Certificate|Status** equal to `Changed`. The adapter log also has a warning that names both thumbprints.

**What it does not do:** it reports a change after the login, so it cannot prevent one. The very first certificate is trusted as it is, because there is nothing to compare it with. To refuse an unknown certificate instead, use `Enabled` or `Pinned`.

### Enabled and Pinned

Use `Enabled` for a vCenter whose certificate comes from a CA that the Cloud Proxy trusts. Use `Pinned` for a self-signed or VMCA-signed certificate, when the customer wants the connection refused rather than reported.

A wrong setting is refused, never treated as "no check": `Pinned` without a thumbprint, a thumbprint that is not SHA-256 or SHA-512, and an unknown mode all stop the connection. **Validate Connection** and the adapter log say what to change.

With `Pinned`, a thumbprint mismatch stops the connection before the user name and password are sent. The same check protects the connection to the vSphere Automation REST API, which reads the Content Libraries: its login is refused on a mismatch, and nothing is sent. The message shows the thumbprint the vCenter presented. Compare it with the certificate in vCenter before you change the setting: a thumbprint copied from a failing connection proves nothing about who answered.

When the vCenter certificate is replaced, `Pinned` needs the new thumbprint. `Enabled` and `Trust on First Use` do not.

### Get the thumbprint

The **SHA-256 Thumbprint** property of the vCenter object already has it, once the pack has collected with `Trust on First Use`. Or, from a machine you trust, with OpenSSL:

```bash
openssl s_client -connect vcenter.example.com:443 -servername vcenter.example.com </dev/null 2>/dev/null \
  | openssl x509 -noout -fingerprint -sha256
```

The output is `sha256 Fingerprint=AB:CD:...`. Paste the part after `=`. Capitals, small letters and `:` between the bytes are all accepted. Check the value against a second source before you rely on it, such as the certificate details in vCenter.

---

## Guest File Transfer TLS Validation

To read Windows Services, OS information and Event Logs, the pack sends a script to the VM and reads its output back. These files do not go through vCenter: vCenter returns a URL on the ESXi host that runs the VM, and the pack transfers the file there over HTTPS.

vCenter records each host's certificate thumbprint when the host is added or reconnected (`host.summary.config.sslThumbprint` in the vSphere API). The pack pins the transfer to it, with no setup.

| Mode | Host certificate matches vCenter's thumbprint | Host certificate differs | vCenter has no thumbprint, or the host is not found |
| :--- | :--- | :--- | :--- |
| `Pinned` (default) | Transferred | **Refused**, the VM is skipped | Transferred unchecked, one warning per host |
| `Strict` | Transferred | **Refused**, the VM is skipped | **Refused**, the VM is skipped |
| `Disabled` | Transferred | Transferred | Transferred |

The certificate is compared during the TLS handshake, so a refused host receives nothing: not the script, and not its output. The reason is in the adapter log. Thumbprints are read from vCenter once per collection, so a replaced ESXi certificate is picked up at the next collection after vCenter has it.

---

## What runs inside a Windows VM

Only when **Guest OS Service Monitoring Status** or **Windows Event Log Monitoring Status** is `Enabled`. Both are `Disabled` by default.

Each PowerShell step in the guest is stopped after 5 minutes, and the VM is skipped for that cycle with a warning. The guest work of one cycle is limited to 30 minutes: when it is spent, the remaining VMs wait for the next cycle, and the log says so.

For every Windows VM whose VMware Tools are running, through the vSphere GuestAPI and the Windows account in the credential:

1. A temporary folder is created under `C:\Windows\Temp`.
2. A PowerShell script that ships inside the pack is copied into it. For Event Logs, an XML file with your Event IDs is copied too.
3. `powershell.exe` runs the script. It reads service status, OS information, or the Event Log IDs you listed.
4. The output file is read back.
5. The folder is deleted. If that fails, the folder stays in the VM.

What this means for a review:

- It is a remote execution path: one credential, held in VCF Operations, can run PowerShell in every VM that the pack monitors. The scripts are fixed. They are not taken from a configuration file.
- The Windows Service names in the configuration file are put in the PowerShell command line. A name is accepted only if it contains letters, digits, space and `_ . $ # @ ( ) + -`, and starts with a letter, digit or `_`. Names with quotes, `;`, `|`, `&`, wildcards or new lines are left out, and one warning in the adapter log names them. So a user who can edit the configuration file cannot make the pack run their own commands in the VMs. This check has no setting: it protects the VMs from the pack's own configuration file, whatever the customer's environment.
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

## Design considerations

**Who secures the certificates.** The customer does. A management pack that stops collecting because a vCenter uses its VMCA certificate punishes the customer for a choice that is theirs, and leaves them blind. So no default refuses a connection because of a certificate. Stricter modes exist for customers whose policy requires them.

**Why Trust on First Use, rather than no check.** No check and Trust on First Use connect in exactly the same cases. But Trust on First Use also tells the customer when the certificate changes, which is the one event that matters: a planned replacement, or another server answering as the vCenter. It costs one TLS handshake per collection, which sends nothing, and it needs no setup. The thumbprint is kept in VCF Operations itself, as a property of the vCenter object, so it survives a Cloud Proxy restart and an upgrade of the pack, and nothing is stored in the container.

**Why not Enabled by default.** The Cloud Proxy does not trust the VMCA, so `Enabled` would stop most installations until someone imports a CA or pins a thumbprint. That is a customer decision, not a default.

**Why a changed vCenter certificate is reported, not refused.** Certificates are replaced on schedule. Refusing would stop collection on every planned replacement, until someone updates the Adapter Instance. Reporting keeps the data flowing and gives the customer the evidence to act on.

**Why a different ESXi certificate is refused, even by default.** Here the pack has a trusted reference with no setup: vCenter's own record of the host's certificate. A host that presents a different certificate is not an insecure environment, it is a server that vCenter does not know, and the pack is about to send it a script that runs with a Windows credential. Skipping that VM for one collection is the safe choice, and it does not stop anything else. When vCenter has no record, there is no reference, so `Pinned` goes ahead and says so.

**Why the service-name check has no setting.** It does not depend on the customer's environment. It closes a hole in the pack itself: without it, a name in the pack's own configuration file could run commands in every monitored VM.

---

## Reporting a vulnerability

Do not open a public issue. See [SECURITY.md](../../SECURITY.md).

---

**Next:** [Customization](customization.md)
