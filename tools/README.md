# Tools

Scripts that are not part of the management pack itself. None of them is in the `.pak` file or runs in VCF Operations. They run on your own machine and talk to VCF Operations over its APIs.

There are two kinds:

- **For VCF Operations administrators:** the importer, which sets up many vCenters at once.
- **For contributors to this repo:** scripts to build the pack, install it on a test instance, check that it works, and check the documentation.

## The tools

| Tool | For | What it does | Changes VCF Operations? | Details |
| :--- | :--- | :--- | :--- | :--- |
| `importer/importer.py` | Administrators | Creates an Adapter Instance, with its credential, for each vCenter in a CSV file | Yes: adds Adapter Instances and credentials | [Bulk Adapter Instance Importer](importer/importer.md) |
| `build/build.ps1` | Contributors | Builds the `.pak` file and pushes the adapter's container image | No | [Build Script](build/build.md) |
| `install/install.ps1` | Contributors | Uploads a `.pak` file to VCF Operations and installs it | Yes: replaces the installed version of the pack | [Install Script](install/install.md) |
| `validate/validate.ps1` | Contributors | Checks that the installed pack collects, and that its data lands on the vCenter objects | No. With `-Release`, it starts a content export job, which changes no content. | [Live Validation Test Plan](validate/validate.md) |
| `check-docs/check_links.py` | Contributors | Checks every relative link and image in the repo's Markdown files | No, it does not connect to anything | [Below](#check-docs) |

## From a code change to a tested build

The contributor tools are used in this order:

1. Change the adapter code in `Management Pack/app`, and run the unit tests: `python -m pytest tests`, from `Management Pack`.
2. `pwsh tools/build/build.ps1`: build the `.pak` file.
3. `pwsh tools/install/install.ps1`: install it on the test instance.
4. After an upgrade, restart collection on the Adapter Instance: see [After an Upgrade: Restart Collection](../docs/installation-guide/installation.md#after-an-upgrade-restart-collection).
5. `pwsh tools/validate/validate.ps1`: check the installed build.

Run `python tools/check-docs/check_links.py` before a commit that changes documentation.

[CONTRIBUTING](../CONTRIBUTING.md) has the testing and documentation rules.

## What you need

| Tool | Needs |
| :--- | :--- |
| `importer.py` | Python 3.9 or later, the `requests` library, and a VCF Operations account that can create Adapter Instances |
| `build.ps1` | PowerShell 7, Python with the [VCF Operations Integration SDK](https://github.com/vmware/vmware-aria-operations-integration-sdk), Docker Desktop, and push access to the container registry |
| `install.ps1` | PowerShell 7, and the local `admin` account of the test instance |
| `validate.ps1` | PowerShell 7, and an account that can read adapters, solutions and resources |
| `check_links.py` | Python 3 and git |

`install.ps1` and `validate.ps1` read the instance's URL and login from `.secrets/vcf-ops.xml`. The file is gitignored, and encrypted for the Windows user who creates it. [Live Validation Test Plan](validate/validate.md#requirements) shows how to create it.

## Other files

- `install/pak-install-requests.md`: the requests the VCF Operations UI makes when it installs a pak, recorded from a browser. `install.ps1` is based on them.
- `importer/vcenter-list-example.csv`: an example input file for the importer.
- `build/mp_build_headless.py`: used by `build.ps1`, not run directly. See [Build Script](build/build.md#why-a-wrapper).

## check-docs

`check_links.py` reads every Markdown file that git tracks. It fails when a relative link or image points to a file that does not exist, or to a heading the target page does not have. It does not check web links.

```
python tools/check-docs/check_links.py
```

It prints the broken links and exits `1`, or prints `0 broken link(s)` and exits `0`. The unit tests run it too (`Management Pack/tests/test_docs_links.py`), so a broken link also fails `pytest`.

A new Markdown file is only checked once git tracks it. Run `git add` first, or `git add -N` to include it without staging its content.
