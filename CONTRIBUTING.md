# Contributing

Thanks for wanting to help. You don't need to be a programmer or a VCF Operations expert: most of the ways to help below take less than an hour.

If you have a GitHub account, star the repository to follow it.

## Ways to help without writing code

| What you can do | Why it helps | How |
| :--- | :--- | :--- |
| **Run the pack and report what you see** | Real environments find problems a lab does not. | Install the pack on a test instance. If something is broken, open a [bug report](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/new/choose) with the version, the Adapter Instance settings without credentials, and the lines from the adapter log. The [Troubleshooting Guide](docs/troubleshooting-guide/first-steps.md) shows where to find them. |
| **Ask for a setting you need** | Your hardening guide may name settings the pack does not collect yet. | Open a [feature request](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/new/choose) with the setting name, its vSphere path, and the guide that names it. Many settings are a one-line change to a configuration file, see [Add a setting](#add-a-setting-to-a-configuration-file). |
| **Improve the documentation** | Many readers never open the code. | Fix a sentence, add an example, or describe a symptom you hit. See [Documentation](#documentation). |
| **Share your content** | Dashboards, reports and super metrics from users make the pack more useful. | Export the dashboard or report from VCF Operations and open a pull request with it, with a short note on what it shows and who it is for. |
| **Tell others** | Many VMware administrators have not heard of the pack. | Write about it, present it at your user group, or point a colleague to the [README](README.md). |

## Add a setting to a configuration file

The pack collects the settings listed in its configuration files, so adding a setting is often a one-line change with no code.

1. Find the setting's path. For a VM advanced parameter, look at `config.extraConfig` in the vCenter Managed Object Browser (`https://<vcenter>/mob`). For an ESXi advanced setting, look at the host's **Configure** tab in vCenter. For a VM option, look at the `config` object in the MOB. A VM option is a vSphere property path, such as `config.flags.diskUuidEnabled`.
2. Open the file under `Management Pack/content/files/solutionconfig/` and add the name on its own line. Put a comma after it unless it is the last entry. If the name is inside a comment, remove the comment markers around it.
3. Check that the file is still valid XML. [Configuration Files](docs/troubleshooting-guide/configuration-files.md) lists the common mistakes.
4. Test it on an instance, see [Testing](#testing).
5. In the pull request, describe the setting: what it is, why it matters, and where you found it.

Settings that only your company needs belong in your own clone of the file in VCF Operations, see [Customization](docs/configuration-guide/customization.md). Change the shipped files only for settings that most users will want.

## Add code

Code contributions are welcome, and you can use an AI coding assistant to write them. The pack is a normal Python project, and the same standard applies to every change, however it was written.

### What we expect from a change

- You understand it. You can explain every line of the pull request, and you have read the code around it.
- It is small and focused, one topic per pull request. A new metric and its documentation can go together. Discuss a rename across the whole project first.
- It has tests. Add worked examples for any formula, in the style of the existing tests. See [Tests](docs/development-guide/tests.md).
- It has documentation. A new metric or setting needs a page, or a row on the right page. See [Documentation](#documentation).
- It contains no secrets: no passwords, tokens, lab IP addresses or credential files in code, tests, docs or screenshots.
- It says how it was made. If an assistant wrote most of it, say so in the pull request, along with what you checked by hand or on an instance. This helps the reviewer and does not count against you.

### Read these first

Start with the [Development Guide](docs/development-guide/repository-layout.md), at least the page for the part you want to change.

| You want to... | Read |
| :--- | :--- |
| Add or change a metric or KPI | [Metrics Code](docs/development-guide/metrics-code.md) and [KPI Scoring Models](docs/concepts/kpi-scoring-models.md) |
| Add or change a property | [Properties](docs/development-guide/properties.md) and [Collectors](docs/development-guide/collectors.md) |
| Add content (dashboards, reports, super metrics) | [Content Folder](docs/development-guide/content-folder.md) |
| Change how the adapter runs | [App Folder](docs/development-guide/app-folder.md) and [The SDK](docs/development-guide/sdk.md) |
| Understand a failure | [Troubleshooting Guide](docs/troubleshooting-guide/first-steps.md) |

### Set up

You need Python 3.12 and Git. The SDK build tool supports Python 3.9 to 3.12, and CI runs 3.12.

```
cd "Management Pack"
python -m pip install -r requirements.txt pytest ruff
python -m pytest tests
python -m ruff check app tests
```

The unit tests also run the documentation link check. To run it on its own, from the repository root:

```
python tools/check-docs/check_links.py
```

CI runs the same tests and lint on every pull request and every push to `main`, plus a security scan of `app` (bandit) and an audit of the runtime dependencies (pip-audit). See [Tests](docs/development-guide/tests.md).

## Workflow

1. For anything bigger than a small fix, open an issue (bug) or a feature request first, so we can agree on the approach. A short description is enough.
2. Fork the repository and create a branch for your change.
3. Make the change, with its tests and documentation.
4. Run the tests, the lint and the link check (above). If you have a test instance, also build, install and run the live validation, see [Tools](tools/README.md). Only the live validation tests the build that is installed on an instance.
5. Open a pull request against `main`. The template asks what changes, why, how you tested it, and whether an assistant was used.
6. Respond to review. A reviewer may ask for a change, a test or a simpler approach. Reviews check correctness and fit with the rest of the pack.

## Issues and planned work

- **Something is broken:** open a GitHub issue with the bug report template. Bugs carry the label `bug`.
- **You want a feature:** open a feature request with its template.
- **Planned enhancements** that the maintainers have accepted are tracked on the [To Do project](https://github.com/users/e1-rahabok/projects/1), one line each, linked to the page that has the details.

## Documentation

The documentation is in `docs/`, and [`docs/README.md`](docs/README.md) lists every page. Each kind of page has its own folder:

| The page is about... | Folder |
| :--- | :--- |
| a model or functional architecture: what the parts are for and how they relate, without formulas | `docs/concepts/` |
| prerequisites and installation, including dark sites | `docs/installation-guide/` |
| what to set after installing: policy, Adapter Instance, customization | `docs/configuration-guide/` |
| how to use the content: dashboards, views, reports | `docs/user-guide/` |
| a metric or KPI (a KPI is a metric): how it is calculated, and its limitations | `docs/reference/metrics/` |
| a list to look things up in, such as keys or settings | `docs/reference/` |
| the code: how a folder or file works, why it is built that way, and how to change it | `docs/development-guide/` |
| problems while the pack runs, and how to find the cause | `docs/troubleshooting-guide/` |

Rules for documentation:

- Describe what is built and why: the design decisions and the alternatives that were considered. A page about a design that is not built yet says so at the top.
- One topic per page. Don't write a step twice; link to the page that has it.
- File names are lowercase, with `-` between words and no spaces. Don't repeat the folder name: `metrics/cluster-risk.md`, not `metrics/cluster-risk-kpi.md`.
- Images go in an `images/` folder next to the page that uses them. KPI formula images go in `docs/reference/metrics/formula/`.
- Links are relative, such as `../configuration-guide/policy.md`.
- Add every new page to the contents in `docs/README.md`.
- Check the links before you commit: `python tools/check-docs/check_links.py`. The unit tests run it too.
- Don't put lab host names, IP addresses or credentials in pages or screenshots.

Small documentation fixes don't need an issue. Open a pull request.

## Testing

Run the unit tests after any change to the adapter code: `python -m pytest tests`, from `Management Pack`. They need no live system.

The live validation tests the build installed on a test instance and only reads from it. Run it with `pwsh tools/validate/validate.ps1`. Its test plan is in [Live Validation Test Plan](tools/validate/validate.md). When KPI code is restructured and its values must not change, also run the [KPI Equivalence Test](tools/equivalence/equivalence.md).

The build needs Docker and PowerShell 7. The install, restart and validation scripts need PowerShell 7. The scripts are described in [Tools](tools/README.md). Don't run the install against an instance you don't own.

## Reporting a problem

Use the [bug report template](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/new/choose). The most useful reports include:

- The pack version and the VCF Operations version.
- What you expected and what you see. A screenshot helps.
- The Validate Connection message if it failed, and the lines of the adapter log around the time of the problem. [Log Messages](docs/troubleshooting-guide/log-messages.md) explains them.
- Whether it happens every cycle or only now and then.

Remove passwords, tokens and private host names before you post.

## Good first contributions

- Correct or clarify a page in `docs/` that confused you.
- Add a setting to a configuration file, tested on your instance.
- Add a worked example to a KPI page from an environment you know.
- Report an error message that does not say what to do, with its text.

## Support

This is a community project with no formal support. Open an issue in this repository, and see [Support](SUPPORT.md) for the team. A question that includes the version, the steps and the log lines gets the fastest answer.
