# Security Policy

This is a community project with no formal support (see [Support](SUPPORT.md)). The maintainers handle security reports on a best-effort basis.

## Reporting a vulnerability

Don't open a public issue with the details of a vulnerability.

Private vulnerability reporting is not enabled on this repository at the moment. Open an issue that says only "security contact requested", with no details, and a maintainer will reply with a private channel.

If the **Security** tab of the repository shows a **Report a vulnerability** button, use that instead.

In your report, include:

- what you found, and the file or setting it is in
- the version or commit
- how to reproduce it, and what an attacker gains

Don't include real credentials, certificates or customer data.

## What to expect

This is a volunteer project, so there is no guaranteed response time. Fixes are released in a new version.

## Scope

In scope:

- The adapter code in `Management Pack/app`, and the content it installs.
- The bulk importer in `tools/importer`.
- How the pack handles credentials and certificates. [TLS and Security Settings](docs/configuration-guide/tls-and-security.md) describes what the pack checks and what it runs in Windows VMs.

Out of scope: vulnerabilities in VCF Operations, vCenter, ESXi or the Integration SDK. Report those to Broadcom.

## Versions

There are no maintenance branches. Fixes go to `main` and ship in the next release.
