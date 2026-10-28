# Contributing

Thank you for wanting to help. You do not need to be a programmer, and you do not need to be an expert in VCF Operations. Every kind of help below is useful, and most of them take less than an hour.

If you have a GitHub account, star the repository so you can follow it. Then pick the way in that suits you.

## Ways to help, without writing code

| What you can do | Why it matters | How |
| :--- | :--- | :--- |
| **Run it and report what you see** | A real environment finds what a lab does not. | Install the pack on a test instance, then open a [bug report](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/new/choose). Include the version, the Adapter Instance settings with the credentials removed, and the lines from the adapter log. The [Troubleshooting Guide](docs/troubleshooting-guide/first-steps.md) shows how to find them. |
| **Ask for a setting you need** | Your hardening guide names settings the pack does not collect yet. | Open a [feature request](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/new/choose) with the setting name, its vSphere path, and the guide that names it. Many settings can be added with a single line in a configuration file, see [Add a setting](#add-a-setting-to-a-configuration-file). |
| **Improve the documentation** | Many readers never open the code, so the docs are the product for them. | Fix a sentence, add an example, or explain a symptom you hit. See [Documentation](#documentation). |
| **Share your content** | Dashboards, reports and super metrics grow the pack for everyone. | Export a dashboard or a report from VCF Operations, and open a pull request with it, with a short note on what it shows and who it is for. |
| **Tell others** | Most VMware administrators have never heard of the pack. | Write about it, present it at your user group, or point a colleague to the [README](README.md). |

## Add a setting to a configuration file

The pack collects the settings listed in its configuration files, so a new setting is often a one-line change, with no code.

1. Find the setting's path. For a VM advanced parameter, look at `config.extraConfig` in the vCenter Managed Object Browser (MOB, at `https://<vcenter>/mob`). For an ESXi advanced setting, look at the host's **Configure** tab in vCenter. For a VM option, look at the `config` object in the MOB.
2. Open the file in the repository, under `Management Pack/content/files/solutionconfig/`, and add the name on its own line. Put a comma after it, unless it is the last one. Remove the comment markers around it if it is inside a comment.
3. Check the file is still valid XML. The [Configuration Files](docs/troubleshooting-guide/configuration-files.md) page lists the common mistakes.
4. Test it on an instance, see [Testing](#testing).
5. Describe the setting in the pull request: what it is, why it matters, and where you saw it.

Settings that a company needs for its own environment are better kept in a clone of the file in VCF Operations, see [Customization](docs/configuration-guide/customization.md). Contribute to the defaults only when the setting is useful to most readers.

## Add code, with or without an AI coding assistant

Everyone is welcome to contribute code, and you are welcome to use an AI coding assistant to write it. The pack is a normal Python project, and the same standard applies whoever or whatever wrote the change.

### What we expect from any change

- **You understand it.** You can explain every line in the pull request, and you have read the code around it. If you cannot explain it, do not submit it.
- **It is small and focused.** One topic per pull request. A new metric and its documentation can go together. A rename across the whole project should be discussed first.
- **It has tests.** Add worked examples for any formula, in the same style as the existing tests. See [Tests](docs/development-guide/tests.md).
- **It has documentation.** A new metric or setting needs a page or a row in the right page. See [Documentation](#documentation).
- **It has no secrets.** No passwords, tokens, IP addresses of your lab, or credential files, in code, tests, docs or screenshots.
- **It says how it was made.** If an assistant wrote most of it, say so in the pull request, and say what you checked by hand or on an instance. This helps the reviewer, it does not count against you.

### Read these first

Read the [Development Guide](docs/development-guide/repository-layout.md), at least the page of the part you want to change. A few minutes there saves hours of review.

| You want to... | Read |
| :--- | :--- |
| Add or change a metric or KPI | [Metrics Code](docs/development-guide/metrics-code.md) and [KPI Scoring Models](docs/concepts/kpi-scoring-models.md) |
| Add or change a property | [Properties](docs/development-guide/properties.md) and [Collectors](docs/development-guide/collectors.md) |
| Add content (dashboards, reports, super metrics) | [Content Folder](docs/development-guide/content-folder.md) |
| Change how the adapter runs | [App Folder](docs/development-guide/app-folder.md) and [The SDK](docs/development-guide/sdk.md) |
| Understand a failure you see | [Troubleshooting Guide](docs/troubleshooting-guide/first-steps.md) |

### Set up

You need Python 3.12 and Git. The SDK requires Python below 3.13.

```
cd "Management Pack"
python -m pip install -r requirements.txt
python -m pytest tests
```

Then check the documentation links from the repository root:

```
python tools/check-docs/check_links.py
```

## The workflow

1. **Open an issue** for anything bigger than a typo, so we can agree on the approach first. A short description is enough.
2. **Fork** the repository, and create a branch for your change.
3. **Make the change**, with its tests and documentation.
4. **Run the tests and the link check** (above). If you have a test instance, run the live validation and the build, see [Tools](tools/README.md). Only the live validation tests the build that is installed on an instance.
5. **Open a pull request** against `main`. Fill in what it changes, why, how you tested it, and whether an assistant was used.
6. **Respond to review.** A reviewer may ask for a change, a test, or a simpler approach. That is normal. Reviews check correctness and fit with the rest of the pack, not who wrote the code.

## Documentation

The documentation is in `docs/`, and [`docs/README.md`](docs/README.md) lists every page. Each kind of page has its own folder:

| The page is about... | Folder |
| :--- | :--- |
| a model or functional architecture: what the parts are for and how they relate, not formulas | `docs/concepts/` |
| what is needed before, and how to install, including dark sites | `docs/installation-guide/` |
| what to set after installing: policy, Adapter Instance, customization | `docs/configuration-guide/` |
| how to use the content: dashboards, views, reports | `docs/user-guide/` |
| a metric or KPI (a KPI is a metric): how it is calculated, its limitations | `docs/reference/metrics/` |
| a list to look up, such as keys or settings | `docs/reference/` |
| the code: how a folder or file works, why it is built that way, and how to change it | `docs/development-guide/` |
| what goes wrong while the pack runs, and how to find out why, for the people who use it | `docs/troubleshooting-guide/` |

The rules, which keep the documentation easy to maintain:

- **Say what is built, and why.** Describe the design decisions and the alternatives weighed. A page for a design that is not built yet says so at the top.
- **Broken is an issue. Anything else is a To Do item.** A GitHub issue is for something that is broken, with the label `bug`. A new feature or a plan is an enhancement, which is not an issue: it is one line in the [To Do list](docs/development-guide/to-do.md), linked to the page that has the details.
- **One topic per page, and no step written twice.** Link to the page that has it.
- **Names are lowercase, with `-` between words, and no spaces.** Do not repeat the folder in the name: `metrics/cluster-risk.md`, not `metrics/cluster-risk-kpi.md`.
- **Images go in an `images/` folder next to the page that uses them.** KPI formula images go in `docs/reference/metrics/formula/`.
- **Links are relative**, such as `../configuration-guide/policy.md`.
- **Every new page is added to the contents of `docs/README.md`.**
- **Check the links** before you commit: `python tools/check-docs/check_links.py`. The unit tests run it too.

Small fixes do not need an issue. Open a pull request straight away.

## Testing

Run the unit tests after any change to the adapter code: `python -m pytest tests`, from `Management Pack`. They need no live system.

The live validation tests the build installed on a test instance. It is read-only. It runs with `pwsh tools/validate/validate.ps1`, and its test plan is in [Live Validation Test Plan](tools/validate/validate.md). When the KPI code is restructured and its values must not change, also run the [KPI Equivalence Test](tools/equivalence/equivalence.md).

The build and the install need Docker and Windows PowerShell 7. The scripts are described in [Tools](tools/README.md). Do not run the install against an instance you do not own.

## Reporting a problem

Use the [bug report template](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/new/choose). The most useful reports say:

- The pack version, and the VCF Operations version.
- What you expected, and what you see. A screenshot helps.
- The Validate Connection message, if it failed, and the lines of the adapter log around the time of the problem. The [Log Messages](docs/troubleshooting-guide/log-messages.md) page explains them.
- Whether it happens every cycle, or now and then.

Remove passwords, tokens, and the names of private hosts before you post.

## Good first contributions

- Correct or clarify a page in `docs/` that confused you.
- Add a setting to a configuration file, with a test on your instance.
- Add a worked example to a KPI page, from an environment you know.
- Report an error message that does not say what to do, with the text.

## Support

This is a community project with no formal support. Submit an issue on this repository, and see [Support](SUPPORT.md) for the team. A question with the version, the steps and the log lines gets the fastest answer.

Thank you for helping. Every issue, every fix and every clear sentence makes the pack more useful to someone who will never read the code.
