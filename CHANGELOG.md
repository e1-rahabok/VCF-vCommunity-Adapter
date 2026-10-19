# Changelog

All notable changes to the VCF Operations vCommunity Management Pack. This file starts with the security changes below. Earlier history is in the Git log.

## Unreleased

### Security

- **The vCenter certificate is now checked.** It was never checked before: the connection was made with certificate validation turned off and no way to change that. New advanced setting **vCenter TLS Validation**: `Enabled` (default), `Pinned` (with **vCenter Thumbprint (SHA-256)**) or `Disabled` (lab only). See [TLS and Security Settings](docs/configuration-guide/tls-and-security.md).
- **ESXi certificates are pinned for guest file transfers.** The 9 transfer calls that used `verify=False` now require the ESXi host certificate to match the thumbprint that vCenter records for the host. New advanced setting **Guest File Transfer TLS Validation**: `Pinned` (default) or `Disabled` (lab only).
- **Windows Service names are validated.** A name from the configuration file with a quote or another shell character could run its own commands in the monitored VMs, under the Windows credential of the adapter. Such names are now left out and named in one adapter log warning.
- `requests` is updated from 2.25.1 to 2.32.4 or later, 3.0 excluded.
- Added [SECURITY.md](SECURITY.md).

### Changed

- **Action needed when upgrading:** an Adapter Instance for a vCenter with a self-signed or internal CA certificate stops connecting until **vCenter TLS Validation** is set to `Pinned` with the thumbprint. See [Upgrading from an earlier version](docs/configuration-guide/tls-and-security.md#upgrading-from-an-earlier-version).
- The bulk importer has the new columns `vcenter_tls_validation`, `vcenter_thumbprint` and `guest_tls_validation`.
- Guest file transfers now time out (10 s to connect, 300 s to read) instead of waiting without a limit.
