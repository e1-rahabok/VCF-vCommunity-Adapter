# First Steps

Start here when the pack does not show the data you expect. These five checks find most problems. Run them in order: each one tells you whether the next is worth doing.

1. [Is the Adapter Instance collecting?](#1-is-the-adapter-instance-collecting)
2. [Does Validate Connection pass?](#2-does-validate-connection-pass)
3. [Are there events on the vCenter object?](#3-are-there-events-on-the-vcenter-object)
4. [Does a known value exist on a vCenter object?](#4-does-a-known-value-exist-on-a-vcenter-object)
5. [Read the adapter log](#5-read-the-adapter-log)

If none of them finds the cause, see [When you ask for help](#when-you-ask-for-help).

## 1. Is the Adapter Instance collecting?

Go to **Administration** > **Integrations** > **Accounts** and find the account under **VCF vCommunity Adapter**.

| Status | What it means | Next |
| :--- | :--- | :--- |
| **Collecting** | The pack runs. | Go to step 4 to check the data. |
| Not collecting, or no status after 5 minutes | The Cloud Proxy cannot run the adapter. | Check that the Cloud Proxy is online and can reach the container registry (or your [dark site](../installation-guide/dark-site.md) registry) and vCenter. See [Symptoms](symptoms.md#the-account-never-shows-collecting). |
| Stopped after an upgrade | The instance did not restart after the new version was installed. | Restart its collection: see [After an Upgrade: Restart Collection](../installation-guide/installation.md#after-an-upgrade-restart-collection). |

## 2. Does Validate Connection pass?

Open the Adapter Instance and click **Validate Connection**. It connects to vCenter with the instance's settings, and the message names what failed.

- If it passes, the connection and the login work. Go to step 3.
- If it fails with a certificate message, the message says what to change, for example that the certificate does not match the thumbprint on the instance. See [TLS and Security Settings](../configuration-guide/tls-and-security.md).
- If it fails with a login or network message, check the credential, the address, the port (443 by default), and that the Cloud Proxy can reach vCenter.

[Symptoms](symptoms.md) lists the other causes and fixes.

## 3. Are there events on the vCenter object?

The pack reports configuration problems as events on the vCenter object. Open the vCenter object in VCF Operations and look at its events.

| Event text starts with | Meaning | Details |
| :--- | :--- | :--- |
| `vCommunity configuration:` | A configuration file is missing, could not be read, or is not valid XML. Nothing is collected from that file. | [Configuration Files](configuration-files.md) |

These events clear by themselves a few collection cycles after the problem is fixed.

A changed vCenter certificate is reported as a property, not an event: `vCommunity|Certificate|Status` reads `Changed` for 24 hours. See [TLS and Security Settings](../configuration-guide/tls-and-security.md).

## 4. Does a known value exist on a vCenter object?

Open the vCenter object, or a cluster or host, and look for `vCommunity|` values. Good ones to check:

- `vCommunity|Configuration|Patch Level` on the vCenter object. Every collection that reaches the vCenter sets it.
- `vCommunity|Collection Health|Warnings in Last Cycle` on the vCenter object: how many warnings and errors the last cycle wrote. When it is above 0, `vCommunity|Collection Health|First Warning` shows the first of them, with the object and the reason. See [Symptoms](symptoms.md#a-collection-warnings-alert-is-shown).
- A KPI on a cluster, such as Cluster Performance Score. It is built from the stats of the vCenter adapter, so it can be blank for a new cluster.

If the vCenter object has no `vCommunity|` value at all, the pack did not reach the vCenter objects. Check step 1, and check that the **vCenter Server** address on the account is the same as on the native vCenter Adapter Instance. See [Symptoms](symptoms.md#the-account-is-collecting-but-the-vcenter-has-no-vcommunity-values).

If some values exist and others don't, the missing ones usually have no input data, which is expected. See [Symptoms](symptoms.md#a-kpi-or-metric-is-blank).

## 5. Read the adapter log

The adapter writes its messages to `adapter.log`, in the container of the Adapter Instance on the Cloud Proxy. Every warning and error has the object it is about. To get the file, generate a support bundle for the Cloud Proxy that runs the Adapter Instance, or ask your VCF Operations administrator for one. [Log Messages](log-messages.md) explains each message.

What to look for:

- An error that names a collection job, such as `Main data collection thread error in collect_host_data`. That job failed for the cycle. The other jobs still ran.
- A warning that names an object, such as `Failed to retrieve ESX configuration properties for : esx01`. Only that object is missing the value.
- `Unexpected collection error`, followed by a traceback. The whole cycle failed. Include the traceback when you ask for help.

## When you ask for help

Include these, so the problem can be reproduced:

1. The pack version, shown under **Administration** > **Integrations** > **Repository**, and the VCF Operations version.
2. The Adapter Instance settings, with the credentials removed.
3. The Validate Connection message, if it failed.
4. The `adapter.log` lines from the time of the problem, or the support bundle.
5. The events on the vCenter object, and the value of `vCommunity|Collection Health|First Warning`.
6. What you expected, and what you see.

Never send passwords, tokens, or the contents of a credential file.

---

**Next:** [Symptoms](symptoms.md) · [Configuration Files](configuration-files.md) · [Log Messages](log-messages.md)
