# Customization

You can **tailor the monitoring scope** for different vCenter servers or environments (e.g., Production vs. Non-Production) by creating your own configuration files instead of using the system-defined defaults.

## Create a Custom Configuration File

1. **Duplicate the default file:** Navigate to **Infrastructure Operations** → **Configurations** → **Management Pack Configuration** → **System Defined**.
2. Locate the desired file (e.g., `esxi_advanced_system_settings.xml`).
3. Click the **Clone** icon to create a copy.
   - **Name the new file** to reflect its purpose (e.g., `esxi_adv_settings_non_prod.xml`).
4. **Edit the new file:** Modify the content of the cloned file to include only the settings or items you wish to monitor for the specific environment.
5. **Reference it in a new Adapter Instance:** Create a new Adapter Instance ([Adapter Instance](adapter-instance.md#1-creating-the-adapter-instance)), but when you reach the **Configuration File Selection** fields, enter the **custom file name** you created (e.g., `esxi_adv_settings_non_prod.xml`).

This is also the right mechanism for scoping *what* gets monitored to match your organization's actual hardening guides, KBs, or internal best practices — see [Introduction](../README.md#the-problem) for why that matters.

---

**Next:** [Metrics and Properties](../reference/metrics-and-properties.md)
