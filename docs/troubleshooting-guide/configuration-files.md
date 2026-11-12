# Configuration Files

The pack collects the settings that its configuration files list. This page covers what happens when a file is wrong, and how to fix it. To create a file, see [Customization](../configuration-guide/customization.md).

- [What a problem looks like](#what-a-problem-looks-like)
- [How to fix it](#how-to-fix-it)
- [The format](#the-format)
- [Mistakes that are easy to make](#mistakes-that-are-easy-to-make)

---

## What a problem looks like

The pack reads each configuration file at every collection. When a file cannot be used, the pack collects nothing from that file, collects everything else as usual, and publishes a warning **event** on the vCenter object. The event text starts with `vCommunity configuration:` and gives the reason.

There are three kinds of problem:

| Event text | Cause |
| :--- | :--- |
| `Configuration file '<name>.xml' could not be read from VCF Operations (HTTP <code>). Nothing is collected from it. Check the file name set on the Adapter Instance.` | VCF Operations has no file with that name. The name on the account is wrong, or the file was deleted or renamed. |
| `Configuration file '<name>.xml' could not be read from VCF Operations (<reason>). Nothing is collected from it this cycle.` | The read itself failed, for example because the connection to VCF Operations dropped. The next cycle tries again. |
| `Configuration file '<name>.xml' is not valid XML (<reason>). Nothing is collected from it until it is corrected.` | The file has an XML error, such as a missing closing tag. The reason in brackets is the parser's. |

The event clears by itself a few collection cycles after the file is fixed. You don't need to delete it.

A wrong name inside the list, such as a misspelt ESXi setting or VM advanced parameter, does not raise an event. That name is not collected. The VM Options file is the exception, because a wrong path there stops the whole VM read. See [Mistakes that are easy to make](#mistakes-that-are-easy-to-make).

## How to fix it

1. **Find the event** on the vCenter object, and note the file name and the reason.
2. **Check the name.** Go to **Infrastructure Operations** > **Configurations** > **Management Pack Configuration**. If no file has that name, correct the name on the account: edit the account and change its configuration file field. Enter the name without `.xml`, because the pack adds it. The fields are listed in [Adapter Instance](../configuration-guide/adapter-instance.md#12-configuration-file-selection).
3. **Check the XML.** Open the file and compare it with the reason in the event. The typical fixes are below.
4. **Save the file.** Wait one collection cycle, then check the vCenter object. The event disappears after a few more cycles.

The files under **System Defined** are the defaults, and an upgrade overwrites them. Don't edit them. Clone the file as described in [Customization](../configuration-guide/customization.md), and edit the clone.

## The format

Five of the six files hold a comma-separated list of names between one pair of tags. Text between `<!--` and `-->` is a comment and is ignored, so only names outside comments are collected. The default files have every name inside a comment, so they collect nothing until you clone one and uncomment the names you want.

| File | Each name is |
| :--- | :--- |
| ESXi Advanced System Settings | an ESXi advanced setting, as shown on the host's **Configure** tab in vCenter |
| ESXi Software Packages | a VIB name |
| VM Advanced Parameters | a key of the VM's `config.extraConfig` |
| VM Options | a vSphere property path under the VM's `config` object, such as `config.flags.diskUuidEnabled` |
| Windows Services | a Windows service name |

A custom VM Options file looks like this. Keep the root tag of the file you cloned:

```xml
<vmConfigs>
  <!-- A comment: ignored. -->
  config.flags.diskUuidEnabled,
  config.bootOptions.efiSecureBootEnabled
</vmConfigs>
```

The names can be on one line or several. The last name has no comma after it.

The Windows Event Log file is different. It is passed to the guest as it is, so it keeps its own structure: `<Log Name="…">` elements that hold `<EventID>` elements. The pack only checks that it is valid XML.

Two XML rules cause most errors:

- Every opening tag needs its closing tag: `<vmConfigs>` ends with `</vmConfigs>`.
- Some characters must be escaped in the text: write `&amp;` for `&` and `&lt;` for `<`.

## Mistakes that are easy to make

| Mistake | What happens | What to do |
| :--- | :--- | :--- |
| The name on the account does not match a file | An event says the file could not be read (HTTP 404). | Correct the name on the account. |
| The name on the account ends in `.xml` | The pack looks for `<name>.xml.xml`, and an event says the file could not be read. | Enter the name without `.xml`. |
| A closing tag is missing, or a tag is misspelt | An event says the file is not valid XML. | Compare the opening and closing tags. |
| A `&` or `<` is typed in the text | An event says the file is not valid XML. | Write `&amp;` or `&lt;`. See [The format](#the-format). |
| An ESXi setting, VIB or VM advanced parameter is misspelt | No event. That name is not collected. | Compare it with the name in vCenter or in the Managed Object Browser (MOB). |
| A VM Options path is misspelt, or does not exist | No event. The read of all VMs fails for the cycle, so no VM gets new values. The log has `Invalid property requested for VirtualMachine: <path>`. | Correct or remove the path. Check it in the MOB, under a VM's `config` object. See [Symptoms](symptoms.md#no-vm-values-after-a-change-to-the-vm-options-file). |
| Every name is inside a comment | No event. The file is valid but the list is empty, so nothing is collected from it. | Remove the `<!--` and `-->` around the names you want. |
| The file was edited under **System Defined** | The next upgrade overwrites the change. | Clone the file, and edit the clone. |

To turn a list off, for example the ESXi software packages, leave the file's text empty or comment out every name. The file stays valid, and nothing is collected from it.

---

**Next:** [Symptoms](symptoms.md) · [Log Messages](log-messages.md) · [First Steps](first-steps.md)
