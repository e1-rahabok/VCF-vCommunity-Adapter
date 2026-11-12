# Bulk Adapter Instance Importer

`importer.py` creates Adapter Instances of the vCommunity Management Pack from a CSV file, one row per vCenter. Use it when you have more vCenters than you want to set up one by one in the UI.

For each row, the script:

1. Creates a credential for the vCenter, or reuses an existing one with the same name.
2. Creates the Adapter Instance with the settings from the row.
3. Assigns the instance to a Collector (Cloud Proxy) or Collector Group, when the row names one.

It uses only the [VCF Operations Suite API](https://developer.broadcom.com/xapis/vcf-operations-api/latest/).

## Requirements

- Python 3.9 or later.
- The [`requests`](https://pypi.org/project/requests/) library: `pip install requests`.
- A VCF Operations account that can create Adapter Instances and credentials.

The script is one file, `importer.py`, and needs no installation.

## Quick start

```bash
# See what would be created, without creating anything
python importer.py --vcf-host vcfops.example.com --vcf-user admin --csv vcenters.csv --dry-run

# Create the instances
python importer.py --vcf-host vcfops.example.com --vcf-user admin --csv vcenters.csv
```

The script prompts for the VCF Operations password, with hidden input, unless you supply it another way. See [Authentication](#authentication).

## Authentication

The VCF Operations password for `--vcf-user` is taken from the first of these that is set:

| Method | How |
| :--- | :--- |
| Command-line option | `--vcf-password '<password>'`. It is visible in shell history and process listings, so use it only for quick local tests. |
| Environment variable | `export VCFOPS_PASSWORD='<password>'` before you run the script. |
| Prompt | Leave both out, and the script asks. Nothing is echoed to the screen. |

The vCenter passwords come from the `vcenter_password` column of the CSV, one per row. See [Security notes](#security-notes).

## Command-line options

| Option | Required | Description |
| :--- | :--- | :--- |
| `--vcf-host` | Yes | VCF Operations FQDN or IP, such as `vcfops.example.com`. `https://` is added when it is missing. |
| `--vcf-user` | Yes | VCF Operations user name, such as `admin`. |
| `--vcf-password` | No | See [Authentication](#authentication). |
| `--csv` | Yes, unless `--list-collectors` is used | Path to the CSV file. |
| `--dry-run` | No | Shows what would be created, without creating or changing anything. |
| `--insecure` | No | Skips the check of the VCF Operations certificate, for a self-signed certificate. |
| `--verbose` | No | Debug logging. |
| `--list-collectors` | No | Lists the Collectors and Collector Groups with their IDs, then exits. Use it to find the value for the `collector_name` column. |

## CSV file format

One row is one vCenter and one Adapter Instance. The header row is required, and the column order does not matter.

Only the three vCenter columns are required. Any other column can be left out or left empty, and the script then uses the same default as the Adapter Instance definition in `Management Pack/app/definition.py`. Keeping the full header row with empty cells is the easiest way to start.

| Column | Required | Default when empty | Description |
| :--- | :--- | :--- | :--- |
| `vcenter_host` | Yes | | vCenter FQDN or IP address. It must match the address of the native vCenter Adapter Instance. |
| `vcenter_user` | Yes | | The vCenter user name the adapter collects with. |
| `vcenter_password` | Yes | | The password of `vcenter_user`, in plain text. See [Security notes](#security-notes). |
| `vcenter_port` | No | `443` | vCenter HTTPS port. |
| `display_name` | No | `vCommunity - <vcenter_host>` | The Adapter Instance name in the VCF Operations UI. |
| `credential_name` | No | `vCommunity Credential - <vcenter_host>` | The name of the credential to create or reuse. Rows with the same name share one credential. See [Credential reuse](#credential-reuse). |
| `esxi_adv_settings_config_file` | No | `esxi_advanced_system_settings` | The configuration file of ESXi advanced settings, without `.xml`. |
| `esxi_vib_driver_config_file` | No | `esxi_packages` | The configuration file of ESXi software packages (VIBs), without `.xml`. |
| `vm_adv_settings_config_file` | No | `vm_advanced_parameters` | The configuration file of VM advanced parameters, without `.xml`. |
| `vm_configuration_config_file` | No | `vm_options` | The configuration file of VM options, without `.xml`. |
| `win_service_config_file` | No | `windows_service_list` | The configuration file of Windows services, without `.xml`. |
| `win_event_config_file` | No | `windows_event_list` | The configuration file of Windows Event Log IDs, without `.xml`. |
| `service_monitoring` | No | `Disabled` | `Enabled` or `Disabled`: Windows Service monitoring, which also collects the Windows OS information. |
| `win_event_monitoring` | No | `Disabled` | `Enabled` or `Disabled`: Windows Event Log monitoring. |
| `vcenter_tls_validation` | No | `Trust on First Use` | How the vCenter certificate is checked: `Trust on First Use`, `Enabled` or `Pinned`. See [TLS and Security Settings](../../docs/configuration-guide/tls-and-security.md#vcenter-tls-validation). |
| `vcenter_thumbprint` | Only with `Pinned` | | SHA-256 or SHA-512 thumbprint of the vCenter certificate, with or without `:`. Required when `vcenter_tls_validation` is `Pinned`, and refused with any other mode. |
| `guest_tls_validation` | No | `Pinned` | How the ESXi host certificate is checked for Windows monitoring: `Pinned`, `Strict` or `Disabled`. See [TLS and Security Settings](../../docs/configuration-guide/tls-and-security.md#guest-file-transfer-tls-validation). |
| `win_user` | No | | Windows user name, needed only when Windows monitoring is enabled. |
| `win_pass` | No | | Windows password, needed only when Windows monitoring is enabled. |
| `collector_name` | No | Chosen by VCF Operations | The name of a Collector (Cloud Proxy) or Collector Group to run the instance on. See [Collector assignment](#collector-assignment). |

The configuration files must exist in VCF Operations under **Management Pack Configuration**. The default files collect nothing until you clone them and uncomment the settings you want: see [Customization](../../docs/configuration-guide/customization.md).

### Settings the CSV does not set

The script also sends the other advanced settings of the Adapter Instance, with their defaults, so that the instance does not show them empty. The CSV cannot change them:

| Setting | Value sent |
| :--- | :--- |
| Cluster Check Period (hours) | `24` |
| Cluster Check Time (UTC) | `00:00` |
| Cluster Check Worst Percent | `5` |
| Monster VM CPU (% of host cores) | `50` |
| Monster VM Memory (% of host DRAM) | `40` |
| Monster VM Memory Minimum (GB) | `256` |

To use other values, edit the Adapter Instance in VCF Operations after the import. The settings are described in [Adapter Instance](../../docs/configuration-guide/adapter-instance.md#2-advanced-settings-optional).

### Example CSV

```csv
vcenter_host,vcenter_port,vcenter_user,vcenter_password,display_name,credential_name,esxi_adv_settings_config_file,esxi_vib_driver_config_file,vm_adv_settings_config_file,vm_configuration_config_file,win_service_config_file,win_event_config_file,service_monitoring,win_event_monitoring,win_user,win_pass,collector_name
vc01.example.com,443,svc-vcfops,SecretPass1!,vCommunity - VC01,vCommunity - Credential,esxi_adv_settings_prod,,,,,,,,,,cloud-proxy-01.example.com
vc02.example.com,443,svc-vcfops,SecretPass1!,vCommunity - VC02,vCommunity - Credential,esxi_adv_settings_prod,,,,,,Enabled,Disabled,svc-winmon,WinPass2!,my-collector-group
vc03.example.com,,svc-vcfops-vc03,AnotherPass3!,,,,,,,,,,,,,
```

- **VC01** runs on a named Cloud Proxy, uses a cloned ESXi settings file, and shares its credential with VC02.
- **VC02** runs on a Collector Group, and turns on Windows Service monitoring with a Windows account.
- **VC03** has only the required columns. Everything else uses the defaults, and VCF Operations chooses the collector.

To refuse an unknown vCenter certificate instead of reporting a change, add the `vcenter_tls_validation` column with `Pinned` and the thumbprint in `vcenter_thumbprint`, or with `Enabled` for a vCenter whose certificate the Cloud Proxy trusts.

`vcenter-list-example.csv`, next to the script, is another example.

## Collector assignment

Put the name of a Collector or of a Collector Group in the `collector_name` column. The script looks the name up in both lists and uses the matching ID. To see the names:

```bash
python importer.py --vcf-host vcfops.example.com --vcf-user admin --list-collectors
```

```
Collectors:
  cloud-proxy-01.example.com                              id=2      state=UP
  VCF Operations Collector-vcfops-01                      id=1      state=UP

Collector Groups:
  my-collector-group                                      id=ca66b8f8-fdc1-477e-8532-bbd6c1c877ed

Use the exact value from the 'name' column above in the collector_name CSV column.
```

Copy the name exactly. Leave `collector_name` empty to let VCF Operations choose.

The column takes a name rather than an ID because the two kinds of ID differ: a Collector's ID is a short number such as `2`, a Collector Group's ID is a UUID, and the **Proxy ID** shown in the UI is a third value that the API does not accept here.

## Credential reuse

When several rows have the same `credential_name`, the credential is created once and used for all of them. This suits vCenters that share one service account.

When a credential with that name already exists in VCF Operations, for example from an earlier run, the script reuses it and logs a notice:

```
[vCommunity - VC01] A credential named 'vCommunity - Credential' already exists - reusing it
(id=15efe2dd-...). NOTE: its stored password was NOT updated from the CSV - if the CSV
password differs from what is currently stored, the adapter instance may fail to authenticate.
```

The script never overwrites the stored password, because other Adapter Instances may use the same credential. To change a password, use the VCF Operations UI or API.

## Security notes

- The CSV file holds vCenter passwords in plain text. When you are done, delete it, or restrict its permissions (`chmod 600 vcenters.csv`). Never commit it to version control.
- Supply the VCF Operations password with the environment variable or the prompt, not with `--vcf-password`.
- `--insecure` turns off the check of the VCF Operations certificate. Use it only for a self-signed certificate on a trusted network.

## Output

At the end, the script prints a summary:

```
======================================================================
RESULT: 3 succeeded, 1 failed (total 4)
======================================================================
  [OK   ] vCommunity - VC01  -  a1b2c3d4-...
  [OK   ] vCommunity - VC02  -  b2c3d4e5-...
  [OK   ] vCommunity - VC03  -  c3d4e5f6-...
  [FAILED] vCommunity - VC04  -  Failed to create adapter instance (HTTP 500): ...
```

It exits `0` when every row succeeded and `1` when any row failed, so you can use it in scripts. Each row is independent: when one vCenter fails, for example with a wrong password, the other rows are still processed.

## Suite API endpoints used

From the [VCF Operations API documentation](https://developer.broadcom.com/xapis/vcf-operations-api/latest/):

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `POST` | `/suite-api/api/auth/token/acquire` | Log in and get a session token |
| `POST` | `/suite-api/api/auth/token/release` | Log out at the end of the run |
| `GET` | `/suite-api/api/credentials` | Find an existing credential by name, when the name is taken |
| `POST` | `/suite-api/api/credentials` | Create a credential |
| `GET` | `/suite-api/api/collectors` | Resolve `collector_name` to a Collector ID |
| `GET` | `/suite-api/api/collectorgroups` | Resolve `collector_name` to a Collector Group ID |
| `POST` | `/suite-api/api/adapters` | Create an Adapter Instance |
