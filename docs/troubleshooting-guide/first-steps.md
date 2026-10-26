# First Steps

Start here when the pack does not show the data you expect. Most problems are found by these five checks, in this order. Each step tells you whether the next one is worth doing.

**On this page:**

1. [Is the Adapter Instance collecting?](#1-is-the-adapter-instance-collecting)
2. [Does Validate Connection pass?](#2-does-validate-connection-pass)
3. [Are there events on the vCenter object?](#3-are-there-events-on-the-vcenter-object)
4. [Does a known value exist on a vCenter object?](#4-does-a-known-value-exist-on-a-vcenter-object)
5. [Read the adapter log](#5-read-the-adapter-log)
- [When you ask for help](#when-you-ask-for-help)

---

## 1. Is the Adapter Instance collecting?

Go to **Administration** → **Integrations** → **Accounts**. Find the **VCF vCommunity Adapter** account.

- **Collecting**: the pack runs. Go to step 4 to check the data.
- **Not collecting, or no status after 5 minutes**: the Cloud Proxy cannot run the adapter. Check that the Cloud Proxy is online, that it can reach the container registry (or your [dark site](../installation-guide/dark-site.md) registry), and that it can reach vCenter. See [Symptoms](symptoms.md#the-account-never-shows-collecting).
- **Stopped after an upgrade**: restart the collection, see [After an Upgrade: Restart Collection](../installation-guide/installation.md#after-an-upgrade-restart-collection).

## 2. Does Validate Connection pass?

Open the Adapter Instance and click **Validate Connection**. It connects to vCenter with the settings of the instance, and the message says what failed.

- **It passes:** the connection and the login are fine. Go to step 3.
- **It fails with a certificate message:** the message says what to change, in plain words, for example that the certificate does not match the thumbprint on the instance. See [TLS and Security Settings](../configuration-guide/tls-and-security.md).
- **It fails with a login or network message:** check the credential, the address and the port (443 by default), and that the Cloud Proxy can reach vCenter.

The full list of symptoms, with their causes and fixes, is in [Symptoms](symptoms.md).

## 3. Are there events on the vCenter object?

The pack reports problems it can see on the vCenter object, as events. Open the vCenter object in VCF Operations and look at its events.

| Event text starts with | Meaning | Where it is explained |
| :--- | :--- | :--- |
| `vCommunity configuration:` | A configuration file is missing or is not valid XML. Nothing is collected from that file. | [Configuration files](configuration-files.md) |

The configuration events clear by themselves a few collection cycles after the problem is fixed.

A change of the vCenter certificate is not an event. It is the property `vCommunity|Certificate|Status`, which reads `Changed` for 24 hours. See [TLS and Security Settings](../configuration-guide/tls-and-security.md).

## 4. Does a known value exist on a vCenter object?

A quick proof that the pack is collecting: open a vCenter cluster or host in VCF Operations and look for a `vCommunity|` value. Good examples:

- `vCommunity|Configuration|Patch Level` on the vCenter object. This is set on every collection that reaches the vCenter.
- A `vCommunity|` metric on a cluster, such as Cluster Performance Score. It needs the stats of the vCenter adapter, so it can be blank for a new cluster.

If the vCenter object has no `vCommunity|` value at all, the pack did not reach the vCenter objects. Check step 1 and the vCenter Server address: it must be the same as the one of the native vCenter Adapter Instance. See [Symptoms](symptoms.md#the-account-is-collecting-but-the-vcenter-has-no-vcommunity-values).

If some values exist and others do not, the value is probably missing data, not a fault. See [Symptoms](symptoms.md#a-kpi-or-metric-is-blank).

## 5. Read the adapter log

The adapter writes its messages to a log file named `adapter.log`, in the container of the Adapter Instance on the Cloud Proxy. Every warning and error the pack writes is in it, with the object it was about. The messages and what to do about each one are in [Log Messages](log-messages.md).

> **To confirm on the lab instance before release:** the exact steps to download the Cloud Proxy support bundle from the VCF Operations UI, and the path of `adapter.log` inside it. Until this is written here, ask the administrator of the VCF Operations instance to provide the support bundle of the Cloud Proxy.

What to look for:

- An **error** line named after the collector, such as `Main data collection thread error in collect_host_data`. That collector failed for the cycle. The other collectors still ran.
- A **warning** line with an object name, such as `Failed to retrieve ... for : esx01`. Only that object lacks the value. Everything else is fine.
- `Unexpected collection error` with a traceback. The whole cycle failed. Send the traceback when you ask for help.

## When you ask for help

Send these, so the problem can be reproduced:

1. The version of the pack, from the account or the manifest, and the VCF Operations version.
2. The Adapter Instance settings, with the credentials removed.
3. The text of the Validate Connection message, if it failed.
4. The lines of `adapter.log` from the time of the problem, or the support bundle.
5. The events on the vCenter object, with their text.
6. What you expected, and what you see.

Do not send passwords, tokens, or the contents of any credential file.

---

**Next:** [Symptoms](symptoms.md) · [Configuration files](configuration-files.md) · [Log Messages](log-messages.md)
