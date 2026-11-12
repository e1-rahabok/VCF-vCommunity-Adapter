# TLS and Security Settings

The pack connects to vCenter with a service account. With Windows monitoring on, it also runs a PowerShell script inside Windows VMs. This page covers how the pack checks certificates on those connections, what it runs in the VMs, and the settings for stricter checks.

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

With the default settings, a certificate problem never stops collection. Many vCenter and ESXi certificates are signed by the VMCA or are self-signed, and the Cloud Proxy does not trust them. Managing those certificates is the customer's job, so the defaults record and compare certificates instead of refusing them:

- **vCenter:** the pack records the vCenter certificate on the first connection, and reports on the vCenter object when it changes. Collection continues.
- **ESXi, for Windows monitoring:** the pack checks each host's certificate against the thumbprint that vCenter records for that host. If vCenter has no thumbprint for the host, the transfer goes ahead and the adapter log says so.

For a check that refuses the connection when it fails, choose a stricter mode on the Adapter Instance.

---

## Settings

The three settings are in the **Advanced Settings** of the [Adapter Instance](adapter-instance.md#2-advanced-settings-optional): **Administration** > **Integrations** > **Accounts** > **VCF vCommunity Adapter** > your instance > **⋮** > **Edit** > **Advanced Settings**.

| Setting | Default | Modes |
| :--- | :--- | :--- |
| **vCenter TLS Validation** | `Trust on First Use` | `Trust on First Use`, `Enabled`, `Pinned` |
| **vCenter Thumbprint (SHA-256)** | *(empty)* | Used only by `Pinned`. |
| **Guest File Transfer TLS Validation** | `Pinned` | `Pinned`, `Strict`, `Disabled`. Used only when Windows monitoring is enabled. |

An Adapter Instance created before these settings existed has them empty, which means the defaults. It keeps connecting as before.

---

## vCenter TLS Validation

| Mode | What the adapter does | When the check fails |
| :--- | :--- | :--- |
| `Trust on First Use` (default) | Connects with any certificate. In every collection it compares the certificate's SHA-256 thumbprint with the one recorded on the vCenter object. | Reports the change and keeps collecting. |
| `Enabled` | Checks the certificate chain and host name against the trust store of the Cloud Proxy. | Does not connect. |
| `Pinned` | Compares the certificate with **vCenter Thumbprint (SHA-256)** before the user name and password are sent. | Does not connect. |

### Trust on First Use

The VCF Operations vCenter account works the same way: you accept the certificate when you add the vCenter. The pack does the same, and then compares the certificate in every collection.

> **Warning.** The user name and password are sent before the certificate is checked. On the first connection, a server that impersonates vCenter receives them. Use `Pinned` or `Enabled` on any network you don't fully trust. The default suits labs and trusted internal networks. The adapter log notes the mode at each connection.

The result is on the **vCenter** object in VCF Operations, under **vCommunity** > **Certificate**:

| Property | Meaning |
| :--- | :--- |
| **SHA-256 Thumbprint** | The thumbprint of the certificate vCenter presents now. It is the value of `openssl x509 -noout -fingerprint -sha256`, in lowercase and without colons. |
| **Status** | `Recorded`: first collection, the certificate is now recorded. `Unchanged`: the same certificate as before. `Changed`: a different certificate, seen within the last 24 hours. `Unknown`: the certificate could not be read in this collection, so nothing was compared. |
| **Previous SHA-256 Thumbprint** | The thumbprint before the last change. |
| **Last Changed** | When the last change was seen, in UTC. |

**When Status is `Changed`:**

- After a planned certificate replacement, this is expected. Status returns to `Unchanged` after 24 hours.
- If nobody replaced the certificate, compare the new thumbprint with the certificate in vCenter. If they differ, another server answered as vCenter and received the service account password. Change the password and investigate.

To get alerted, create a symptom on the vCenter property **vCommunity|Certificate|Status** equal to `Changed`. The adapter log also has a warning with both thumbprints.

Trust on First Use detects a change after the login, so it cannot prevent one. It also trusts the very first certificate, because there is nothing to compare it with. To refuse an unknown certificate, use `Enabled` or `Pinned`.

### Enabled and Pinned

Use `Enabled` when the vCenter certificate comes from a CA that the Cloud Proxy trusts. Use `Pinned` for a self-signed or VMCA-signed certificate when you want the connection refused instead of reported.

A wrong setting stops the connection instead of turning the check off. `Pinned` without a thumbprint, a thumbprint that is not SHA-256 or SHA-512, and an unknown mode are all refused. **Validate Connection** and the adapter log say what to change.

With `Pinned`, a thumbprint mismatch stops the connection before the user name and password are sent. The same pin protects the connection to the vSphere Automation REST API, which the pack uses to read content libraries: on a mismatch its login is refused and nothing is sent. The REST connection accepts only a SHA-256 thumbprint, so use SHA-256 with `Pinned`. With `Trust on First Use`, the REST connection is not checked, the same as the main connection.

The error message shows the thumbprint vCenter presented. Compare it with the certificate in vCenter before you change the setting: a thumbprint copied from a failing connection proves nothing about who answered.

When the vCenter certificate is replaced, `Pinned` needs the new thumbprint. `Enabled` and `Trust on First Use` don't.

### Get the thumbprint

Once the pack has collected with `Trust on First Use`, the **SHA-256 Thumbprint** property of the vCenter object has it. You can also read it with OpenSSL from a machine you trust:

```bash
openssl s_client -connect vcenter.example.com:443 -servername vcenter.example.com </dev/null 2>/dev/null \
  | openssl x509 -noout -fingerprint -sha256
```

The output is `sha256 Fingerprint=AB:CD:...`. Paste the part after `=`. Uppercase, lowercase and `:` between the bytes are all accepted. Check the value against a second source, such as the certificate details in vCenter, before you rely on it.

---

## Guest File Transfer TLS Validation

To read Windows services, OS information and event logs, the pack copies a script to the VM and reads its output back. These files don't pass through vCenter: vCenter returns a URL on the ESXi host that runs the VM, and the pack transfers the file to that host over HTTPS.

vCenter records each host's certificate thumbprint when the host is added or reconnected (`host.summary.config.sslThumbprint` in the vSphere API). The pack pins the transfer to that thumbprint, with no setup.

| Mode | Host certificate matches vCenter's thumbprint | Host certificate differs | vCenter has no thumbprint, or the host is not found |
| :--- | :--- | :--- | :--- |
| `Pinned` (default) | Transferred | Refused, the VM is skipped | Transferred unchecked, with one warning per host |
| `Strict` | Transferred | Refused, the VM is skipped | Refused, the VM is skipped |
| `Disabled` | Transferred | Transferred | Transferred |

The certificate is compared during the TLS handshake, so a refused host receives nothing: neither the script nor its output. The reason is in the adapter log. The pack reads the thumbprints from vCenter once per collection, so a replaced ESXi certificate is picked up at the next collection after vCenter has it.

---

## What runs inside a Windows VM

This happens only when **Guest OS Service Monitoring Status** or **Windows Event Log Monitoring Status** is `Enabled`. Both are `Disabled` by default.

For every Windows VM with VMware Tools running, the pack uses the vSphere Guest Operations API and the Windows account in the credential to:

1. Create a temporary folder under `C:\Windows\Temp`.
2. Copy a PowerShell script that ships inside the pack into it. For event logs, it also copies an XML file with your event IDs.
3. Run the script with `powershell.exe`. The script reads service status and OS information, or the event IDs you listed.
4. Read the output file back.
5. Delete the folder. If that fails, the folder stays in the VM.

Each PowerShell step in a guest is stopped after 5 minutes, and that VM is skipped for the cycle with a warning. All guest work in one cycle is limited to 30 minutes: when the time is used up, the remaining VMs wait for the next cycle, and the log says so. At most 100 events per VM are collected in a cycle.

Points for a security review:

- This is a remote execution path. One credential, stored in VCF Operations, can run PowerShell in every VM the pack monitors. The scripts are fixed in the pack. They are not read from a configuration file.
- The Windows service names from the configuration file are put on the PowerShell command line. A name is accepted only if it contains letters, digits, spaces and `_ . $ # @ ( ) + -`, and starts with a letter, digit or `_`. Names with quotes, `;`, `|`, `&`, wildcards or line breaks are dropped, and one warning in the adapter log names them. A user who can edit the configuration file therefore cannot make the pack run other commands in the VMs. This check has no setting.
- Event IDs are sent as an XML file and read as data. They are not part of a command line.
- The Windows account needs no administrator rights, see [User Account Requirements](../installation-guide/system-requirements.md#user-account-requirements). Don't use a local Administrator account. The vCenter account needs the guest operations privileges listed on the same page.

Windows monitoring adds load to VCF Operations and to the VMs. See [Before you turn on Windows monitoring](adapter-instance.md#before-you-turn-on-windows-monitoring).

---

## Container registry

The Cloud Proxy pulls the adapter image from `ghcr.io`. In a regulated environment, you can use a private registry instead of opening `ghcr.io` to every Cloud Proxy, see [Dark Site Installation](../installation-guide/dark-site.md). You then pull, scan and approve the image once, and the Cloud Proxies don't depend on a third-party registry.

---

## Accounts

- Give the pack its own vCenter service account with the read-only role and only the extra privileges it needs. Don't share it with other tools. See [User Account Requirements](../installation-guide/system-requirements.md#user-account-requirements).
- Use a separate Windows account for guest monitoring, and only when you turn it on.
- Leave the software package and Windows configuration files without active entries until you need them.

---

## Design considerations

**Who secures the certificates.** The customer does. If a management pack stopped collecting because a vCenter uses its VMCA certificate, the customer would lose monitoring over a choice that is theirs to make. So no default refuses a connection because of a certificate. Stricter modes are there for customers whose policy requires them.

**Why Trust on First Use instead of no check.** Both connect in exactly the same cases, but Trust on First Use also reports when the certificate changes. That happens either because of a planned replacement or because another server answered as vCenter, and both are worth knowing. It costs one TLS handshake per collection, which sends no credentials, and it needs no setup. The thumbprint is stored in VCF Operations as a property of the vCenter object, so it survives a Cloud Proxy restart and a pack upgrade, and nothing is stored in the container.

**Why not `Enabled` by default.** The Cloud Proxy does not trust the VMCA, so `Enabled` would stop most installations until someone imports a CA certificate or pins a thumbprint. That is a decision for the customer.

**Why a changed vCenter certificate is reported and not refused.** Certificates are replaced on a schedule. Refusing would stop collection at every planned replacement until someone updates the Adapter Instance. Reporting keeps the data coming and gives the customer what they need to act.

**Why a different ESXi certificate is refused by default.** For ESXi the pack has a trusted reference with no setup: vCenter's own record of the host certificate. A host that presents a different certificate is a server vCenter does not know, and the pack is about to send it a script that runs with a Windows credential. Skipping that VM for one collection is the safe choice and does not affect anything else. When vCenter has no record, there is no reference, so `Pinned` goes ahead and logs a warning.

**Why the service name check has no setting.** It does not depend on the environment. It closes a gap in the pack itself: without it, a name in the pack's own configuration file could run commands in every monitored VM.

---

## Reporting a vulnerability

Don't open a public issue. See [SECURITY.md](../../SECURITY.md).

---

**Next:** [Included Content](../user-guide/included-content.md)
