# Tools

Scripts that are not part of the management pack. None of them is in the `.pak` file or runs in VCF Operations. They run on your own machine and use the VCF Operations APIs.

- **For VCF Operations administrators:** the importer, which creates Adapter Instances for many vCenters at once, and the Summary dashboard script, which binds a dashboard to an object type's Summary tab.
- **For contributors to this repo:** scripts that build the pack, install it on a test instance, restart its collection, check that it works, take the documentation's screenshots, check the documentation's links, and check the evidence in the engineering review.

## The tools

| Tool | For | What it does | Changes VCF Operations? | Details |
| :--- | :--- | :--- | :--- | :--- |
| `importer/importer.py` | Administrators | Creates an Adapter Instance, with its credential, for each vCenter in a CSV file | Yes: adds Adapter Instances and credentials | [Bulk Adapter Instance Importer](importer/importer.md) |
| `summary_dashboard/set_summary_dashboard.py` | Administrators | Replaces the Summary tab of one object type with a dashboard, or restores the built-in page | Yes: changes the Summary tab of the object type | [Summary Dashboard Script](summary_dashboard/summary_dashboard.md) |
| `build/build.ps1` | Contributors | Builds the `.pak` file and pushes the adapter's container image | No | [Build Script](build/build.md) |
| `install/install.ps1` | Contributors | Uploads a `.pak` file to VCF Operations and installs it | Yes: replaces the installed version of the pack | [Install Script](install/install.md) |
| `restart/restart.ps1` | Contributors | Stops and starts collection on every Adapter Instance of this pack, and waits until each one collects again | Yes: the pack's collection stops for a moment | [Restart Script](restart/restart.md) |
| `validate/validate.ps1` | Contributors | Checks that the installed pack collects, and that its data lands on the vCenter objects | No. With `-Release`, it starts a content export job, which changes no content. | [Live Validation Test Plan](validate/validate.md) |
| `screenshot/screenshot.ps1` | Contributors | Takes the documentation's screenshots of the VCF Operations UI, as defined in `screenshots.json`, and saves them into `docs/` | No: it only opens pages and expands sections | [Screenshot Script](screenshot/screenshot.md) |
| `check-docs/check_links.py` | Contributors | Checks every relative link and image in the repo's Markdown files | No, it connects to nothing | [Below](#check-docs) |
| `review/review.py` | Contributors | Checks an engineering review's evidence: that each cited file and line exists, that each finding has a decision with its evidence, and which test counts and Python versions the pages state. It can also record a snapshot of the code's facts | No, it reads the repo and runs `git` read commands only | [Review Evidence Tool](review/review.md) |
| `equivalence/planned_cases.py`, `equivalence/compare.py` | Contributors | Runs about 3,400 planned cases through two copies of the KPI code, before and after a restructure, and lists every difference in what they publish | No, it connects to nothing | [KPI Equivalence Test](equivalence/equivalence.md) |

## From a code change to a tested build

Contributors use the tools in this order:

1. Change the adapter code in `Management Pack/app`, and run the unit tests with `python -m pytest tests` from `Management Pack`. If you restructured KPI code whose values must not change, also run the [KPI Equivalence Test](equivalence/equivalence.md).
2. `pwsh tools/build/build.ps1` builds the `.pak` file.
3. `pwsh tools/install/install.ps1` installs it on the test instance.
4. `pwsh tools/restart/restart.ps1` restarts collection on the Adapter Instances, which often stop collecting after an upgrade. See [After an Upgrade: Restart Collection](../docs/installation-guide/installation.md#after-an-upgrade-restart-collection).
5. Wait one collection cycle, then run `pwsh tools/validate/validate.ps1` to check the installed build.

Run `python tools/check-docs/check_links.py` before you commit a documentation change. When the UI or the pack's settings change, run `pwsh tools/screenshot/screenshot.ps1` to update the screenshots.

[CONTRIBUTING](../CONTRIBUTING.md) has the testing and documentation rules.

## What you need

| Tool | Needs |
| :--- | :--- |
| `importer.py` | Python 3.9 or later, the `requests` library, and a VCF Operations account that can create Adapter Instances and credentials |
| `set_summary_dashboard.py` | Python 3, the `requests` library, and a local VCF Operations account that can manage dashboards, such as `admin` |
| `build.ps1` | PowerShell 7, Python 3.9 to 3.12 with the [VCF Operations Integration SDK](https://github.com/vmware/vmware-aria-operations-integration-sdk) 1.3 or later, Docker Desktop, and push access to the container registry |
| `install.ps1` | PowerShell 7, and the local `admin` account of the test instance |
| `restart.ps1` | PowerShell 7, and an account that can stop and start collection on Adapter Instances |
| `validate.ps1` | PowerShell 7, and an account that can read adapters, solutions and resources |
| `screenshot.ps1` | PowerShell 7, Python with Playwright (`python -m pip install --user playwright`), Google Chrome, and an account that can see the pages of the screenshots |
| `check_links.py` | Python 3 and git |
| `planned_cases.py`, `compare.py` | The Python that runs the unit tests, and a second copy of the code, for example a `git worktree` |

`install.ps1`, `restart.ps1`, `screenshot.ps1` and `validate.ps1` read the instance's URL and login from `.secrets/vcf-ops.xml`. The file is gitignored, and encrypted for the Windows user who creates it. [Live Validation Test Plan](validate/validate.md#requirements) shows how to create it. `set_summary_dashboard.py` reads the connection from the `VCFOPS_HOST`, `VCFOPS_USER` and `VCFOPS_PW` environment variables.

## Other files

- `install/pak-install-requests.md`: the requests the VCF Operations UI makes when it installs a pak, recorded from a browser. `install.ps1` is built on them.
- `importer/vcenter-list-example.csv`: an example input file for the importer.
- `summary_dashboard/ui_client.py`: the VCF Operations UI session client that `set_summary_dashboard.py` uses. It is adapted from the vcf-content-factory project. See [Summary Dashboard Script](summary_dashboard/summary_dashboard.md#files).
- `screenshot/screenshot.py` and `screenshot/screenshots.json`: the engine of `screenshot.ps1`, and the definition of each screenshot. See [Adding a screenshot](screenshot/screenshot.md#adding-a-screenshot).
- `build/mp_build_headless.py`: used by `build.ps1`, not run directly. See [Build Script](build/build.md#why-a-wrapper).
- `review/review.py`: the evidence checks for the [Engineering Review](../docs/development-guide/engineering-review/README.md). It is read-only and not run by CI. Run it with Python 3, from the repository root: `python tools/review/review.py check`.

## check-docs

`check_links.py` reads every Markdown file that git tracks. It fails when a relative link or image points to a file that does not exist, or to a heading the target page does not have. It does not check web links.

```
python tools/check-docs/check_links.py
```

It prints the broken links and exits `1`, or prints `0 broken link(s)` and exits `0`. The unit tests run it too (`Management Pack/tests/test_docs_links.py`), so a broken link also fails `pytest`.

A new Markdown file is checked only once git tracks it. Run `git add` first, or `git add -N` to include it without staging its content.

## Certificates

`install.ps1`, `restart.ps1`, `validate.ps1` and `screenshot.ps1` do not check the TLS certificate of the instance (`-SkipCertificateCheck`), and `set_summary_dashboard.py` connects with `verify_ssl=False`. They are meant for a test instance on a trusted network. Before you use them against a production instance, make sure you can trust its certificate. See [TLS and Security Settings](../docs/configuration-guide/tls-and-security.md).
