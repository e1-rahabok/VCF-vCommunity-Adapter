# Security Policy

This is a community project with no formal support (see [Support](SUPPORT.md)). Security reports are still welcome, and are handled on a best-effort basis by the maintainers.

## Reporting a vulnerability

**Do not open a public issue for a vulnerability.**

Use GitHub's private report: open the **Security** tab of this repository, choose **Report a vulnerability**, and describe:

- what you found, and the file or setting it is in,
- the version or commit,
- how to reproduce it, and what an attacker gains.

Please do not include real credentials, certificates or customer data.

If the **Report a vulnerability** button is not shown, private reporting is not enabled on this repository yet. Open an issue that says only "security contact requested", with no detail, and a maintainer will reply with a private channel.

## What to expect

This is a volunteer project, so there is no guaranteed response time. A fix is released in a new version.

## What is in scope

- The adapter code in `Management Pack/app`, and the content it installs.
- The bulk importer in `tools/importer`.
- How the pack handles credentials and certificates. See [TLS and Security Settings](docs/configuration-guide/tls-and-security.md) for what the pack checks and what it runs in Windows VMs.

Out of scope: a vulnerability in VCF Operations, vCenter, ESXi, or the Integration SDK itself. Report those to Broadcom.

## Versions

There are no maintenance branches. Fixes go to the main branch and the next release.
