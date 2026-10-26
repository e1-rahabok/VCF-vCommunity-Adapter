# Configuration Files

The pack collects what its configuration files list. This page is about what happens when one of them is wrong, and how to fix it. For creating a file, see [Customization](../configuration-guide/customization.md).

**On this page:** [What a problem looks like](#what-a-problem-looks-like) · [How to fix it](#how-to-fix-it) · [The format](#the-format) · [Mistakes that are easy to make](#mistakes-that-are-easy-to-make)

---

## What a problem looks like

The pack reads each configuration file at every collection. If a file cannot be used, the pack does two things:

1. It collects nothing from that file, and everything else is collected as usual. One bad file never stops the others.
2. It publishes an **event** on the vCenter object, named `vCommunity configuration: …`, with the reason. The event is a warning.

Two kinds of problem exist:

| Event says | Cause | What you see |
| :--- | :--- | :--- |
| `Configuration file 'name.xml' could not be read from VCF Operations (HTTP 404)` | The file is not there. The name set on the account is wrong, or the file was deleted or renamed. | The settings of that file are not collected at all. |
| `Configuration file 'name.xml' is not valid XML (…)` | The file has a mistake in its XML, such as a missing closing tag. The reason in brackets says what the parser found. | The settings of that file are not collected at all. |

The event clears by itself a few collection cycles after the file is fixed. You do not need to delete it.

Note that a **wrong name in the list**, such as a misspelt setting, is not an event. The name is not collected, and the file is otherwise fine. See [Mistakes that are easy to make](#mistakes-that-are-easy-to-make).

## How to fix it

1. **Find the event** on the vCenter object in VCF Operations. Read the file name and the reason in brackets.
2. **Check the name.** Go to **Infrastructure Operations** → **Configurations** → **Management Pack Configuration**. If the file is not there with that name, the name is wrong. Correct the name on the account: edit the account, and change its configuration file field. The field names are in [Adapter Instance](../configuration-guide/adapter-instance.md#12-configuration-file-selection).
3. **Check the XML.** Open the file, and check the reason. Typical fixes are below.
4. **Save the file.** Wait one collection cycle, then check the vCenter object. The event disappears after a few more cycles.

A file under **System Defined** is the default. Do not edit it: the upgrade overwrites it. Clone it, as described in [Customization](../configuration-guide/customization.md), and edit the clone.

## The format

Each file is an XML document. Its text, between the tags, is a list of names separated by commas. Lines that start with `<!--` and end with `-->` are comments, and they are ignored. Only uncommented names are collected.

A valid custom file for VM options looks like this. The root tag must match the one of the file you cloned, and the names are separated by commas:

```xml
<vmConfigs>
  <!-- A comment: ignored. -->
  disk.EnableUUID, tools.syncTime
</vmConfigs>
```

The list can also be written on several lines. The last name needs no comma.

Two XML rules cause most errors:

- **Every opening tag needs its closing tag.** `<vmConfigs>` ends with `</vmConfigs>`.
- **Certain characters must be escaped in the text.** Write `&amp;` for `&`, and `&lt;` for `<`.

## Mistakes that are easy to make

| Mistake | What happens | What to do |
| :--- | :--- | :--- |
| The name on the account does not match the file | An event says the file could not be read. | Correct the name on the account. |
| A closing tag is missing, or a tag is misspelt | An event says the file is not valid XML. | Compare the opening and closing tags. |
| A setting name is misspelt | No event. The setting is not collected. | Compare it with the name shown in vCenter, such as in the MOB. |
| Everything is inside a comment | No event. The file is valid, but the list is empty, so nothing is collected from it. | Remove the `<!--` and `-->` around the lines you want. |
| The file was edited under **System Defined** | The upgrade overwrites the change. | Clone the file, and edit the clone. |
| A `&` or a `<` is typed in the text, not escaped | An event says the file is not valid XML, with the reason. | Write `&amp;` and `&lt;`. See [The format](#the-format). |

To empty a list on purpose, such as to switch off the ESXi software packages, leave the text of the file empty, or comment out every name. The file is still valid, and nothing is collected from it.

---

**Next:** [Symptoms](symptoms.md) · [Log Messages](log-messages.md) · [First Steps](first-steps.md)
