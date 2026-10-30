# 29 Oct 2026 Completed

This page is the response to the [29 Oct 2026 Review](2026-10-29-review.md). It records, for each finding, the
decision and the action taken.

> **Status (2026-10-30):** version 0.7.0 is built, installed on the test instance, and passes the standard live
> validation (16 pass, 4 warn, 0 fail). The fixes are on the `0.7.0-review-fixes` branch and are not released yet.
> The log checks, the lint findings and the release are still open. See [Open items](#open-items).

## Decisions

Each finding has one decision:

- **Implemented.** The change is made in the code, the tests or the docs.
- **Partly.** Part of the change is made. The rest is open, and the page says what is left.
- **Deferred.** Accepted, but not in 0.7.0. It is an open item, or a line on the To Do project.
- **Rejected.** No change. The reason is given.
- **No change.** A positive or information finding. Nothing to do.

## Decisions with reasons

- **SEC-01 (Partly).** The default TLS mode stays Trust on First Use. It is a documented decision for internal VMware
  environments. The warning is added. The stronger pre-login thumbprint check is not in the 0.7.0 plan.
- **SEC-03 (Rejected).** ESXi SHA-1 thumbprints are a limit of what vCenter provides. The trust model does not change
  without a migration plan. The limit stays documented.
- **SEC-05 (Implemented).** The XML parser is kept. The alternative, `defusedxml`, was considered and not adopted. The
  input is written only by VCF Operations administrators. A new runtime dependency would need its own audit and an
  install on the test instance. Revisit this if anyone other than an administrator can write these files.
- **BUG-02 (Implemented).** The documentation was corrected first, as the reviewer asked. The code cache was then
  removed. It never survived between cycles, so no cross-cycle cache was needed.
- **GOV-04 (Partly).** No changelog file is added. Release notes go on GitHub. The tag `v0.7.0` is made at release.
- **Python version (open, issue #66).** The decision is open. CI uses 3.12 for now. The 0.7.0 unit tests pass on 3.12.10
  (476 passed). The 0.7.0 build ran on 3.12.

## Actions by finding

### 1. Security

| ID | Decision | Action taken |
| :--- | :--- | :--- |
| SEC-01 | Partly | A warning is in the setting's description, in the docs, and in the log at each connection. The log line is at information level, so the alert does not fire. The default is unchanged. The pre-login thumbprint check is not in the plan. |
| SEC-02 | Implemented | The REST login is pinned during the handshake, and the separate probe is removed. Issue #65. |
| SEC-03 | Rejected | No change. The limit stays documented. |
| SEC-04 | Implemented | The mismatch text is a named constant. A test checks it against the installed urllib3. |
| SEC-05 | Implemented | The XML parser is documented with its threat model, and marked for bandit. Each XML call in `utils/config_files.py`, and the import in `adapter.py`, carries a `nosec` marker that gives the SEC-05 reason. |
| SEC-06 | Deferred | Not in the 0.7.0 plan. The lab-only wording is still to be added to the docs. |
| SEC-07 | Implemented | `ServiceContent` is no longer logged. |
| SEC-08 | Implemented | `gh pr merge` is removed from the project allow-list. |
| SEC-09 | Implemented | The curly-quote case already had a test (`tests/test_guest_args.py`). |

### 2. Reliability and correctness

| ID | Decision | Action taken |
| :--- | :--- | :--- |
| BUG-01 | Implemented | Guest polling is bounded. The process is stopped after 5 minutes. Issue #53. |
| BUG-02 | Implemented | The dead hourly cache is removed. The documentation says the libraries are read in every cycle. Issue #54. |
| BUG-03 | Implemented | Guest CSV parsing is fixed, with tests. Issues #55 to #58. |
| BUG-04 | Implemented | Guest error paths are fixed, with tests. Issues #55 to #58. |
| BUG-05 | Implemented | Guest error paths are fixed, with tests. Issues #55 to #58. |
| BUG-06 | Implemented | Guest message format is fixed, with tests. Issues #55 to #58. |
| BUG-07 | Implemented | `vm_name` is set before the `try`. Issue #59. |
| BUG-08 | Partly | The warning names how many resources have no value. Issue #60 stays open: the callers still publish totals from partial data. There are 42 call sites in 19 files. Each one needs its own rule for a partial total. |
| BUG-09 | Implemented | The return is out of `finally`. Issue #61. |
| BUG-10 | Implemented | A failed vCenter read raises. Issue #62. |
| BUG-11 | Implemented | The event list read is isolated. Issue #63. |
| BUG-12 | Implemented | The event query is bounded. Issue #64. |
| BUG-13 | Implemented | The unused `mode` parameter is removed. |

### 3. Concurrency

| ID | Decision | Action taken |
| :--- | :--- | :--- |
| CON-01 | Deferred | Needs a test against a real vCenter. Live test on the To Do project. |
| CON-02 | Deferred | Not in the 0.7.0 plan. |
| CON-03 | Implemented | The futures map to their job names with a dictionary. |

### 4. Scalability and performance

| ID | Decision | Action taken |
| :--- | :--- | :--- |
| SCL-01 | Partly | A guest time budget of 30 minutes per cycle is added. The job count is open: To Do project. |
| SCL-02 | Deferred | Bulk list endpoints. To Do project. |
| SCL-03 | Implemented | At most 100 events per VM per cycle, with a warning when more are found. |
| SCL-04 | No change | Positive. Kept. |
| SCL-05 | Partly | The separate probe in the library collector is removed (SEC-02). The other logins are unchanged. Documenting why they are separate is not in the plan. |

### 5. Maintainability and readability

| ID | Decision | Action taken |
| :--- | :--- | :--- |
| MNT-01 | Implemented | `collect()` is split into `_collect_cycle` and `_run_object_jobs`. The definition split is on the To Do project. |
| MNT-02 | Implemented | The Windows guest settings are one `GuestSettings` object. |
| MNT-03 | Implemented | The error rule is written in [App Folder](../app-folder.md#conventions). |
| MNT-04 | Implemented | The shared guest helper is `utils/guest_ops.py`. |
| MNT-05 | Implemented | The commented-out imports are removed. |
| MNT-06 | Partly | Unused imports are fixed. 12 ruff findings remain: B009 (5), B905 (4) and B017 (3). B905 and B017 change behaviour or test strictness, so each needs a decision. |
| MNT-07 | Implemented | The TODO is removed from the code. The item is on the To Do project. |
| MNT-08 | Deferred | Not in the 0.7.0 plan. |
| MNT-09 | No change | Acceptable. Split by object type if it grows. |

### 6. Testing

| ID | Decision | Action taken |
| :--- | :--- | :--- |
| TST-01 | Implemented | Tests pass on Python 3.12.10 (476 passed, no skips). The standard live validation passed. The log checks are open. |
| TST-02 | Implemented | Tests for the guest helpers, the collectors, the timeout and the failure paths. They use fakes, so no VM is needed. |
| TST-03 | Implemented | Done through GOV-02. CI runs the tests. |
| TST-04 | Implemented | Fault-injection tests for the timeout and the failure paths. |
| TST-05 | Partly | Ruff runs on 0.7.0. The 12 remaining findings are listed under MNT-06. |
| TST-06 | No change | Positive. Kept. |

### 7. Documentation

| ID | Decision | Action taken |
| :--- | :--- | :--- |
| DOC-01 | Implemented | The 12 metric pages are listed in the docs index. |
| DOC-02 | Implemented | The library documentation matches the code. |
| DOC-03 | Implemented | The review is split into dated pages: the review, this page, and the re-score. |
| DOC-04 | No change | Positive. Kept. |

### 8. Repository hygiene and governance

| ID | Decision | Action taken |
| :--- | :--- | :--- |
| GOV-01 | Implemented | The `.DS_Store` files are removed from Git, and `.DS_Store` is ignored. |
| GOV-02 | Implemented | CI workflow (`.github/workflows/ci.yml`), lint rules (`ruff.toml`), and a pull request template. |
| GOV-03 | Partly | Dependabot for pip and GitHub Actions, and `CODEOWNERS`, are added. Secret scanning and CodeQL are open: To Do project. |
| GOV-04 | Partly | No changelog file (see above). Tag `v0.7.0` at release. |
| GOV-05 | Deferred | To Do project. |
| GOV-06 | Deferred | To Do project. Update the dependency set before the release. |
| GOV-07 | Implemented | `.venv*/` is ignored in the root `.gitignore`. |
| GOV-08 | Implemented | The placeholder folders are documented in [Content Folder](../content-folder.md). |

## Open items

- [ ] BUG-08 (issue #60): callers do not skip the resources of a failed batch.
- [ ] MNT-06, TST-05: 12 ruff findings (B009, B905, B017). Each needs a decision.
- [ ] GOV-04: tag `v0.7.0` when it is released.
- [ ] SCL-01 (job count), SCL-02, CON-01 (live test), GOV-03 (secret scanning and CodeQL), GOV-05, GOV-06, MNT-01 (the
  definition split): on the To Do project, one line each.
- [ ] SEC-06, CON-02, MNT-08: deferred, with no To Do line yet. Add one line each.
- [ ] Python version (issue #66): the decision is open. CI uses 3.12 for now.
- [ ] Live checks of 0.7.0 on the test instance (issue #2, `verify-live`). The log checks are still to do: the TLS
  message, the Windows guest properties and event counts, the content libraries, and the failure paths.

## Verification

- **Unit tests:** 476 passed on Python 3.12.10 (Build Laptop, 2026-10-30), with no skips. They include the docs link
  check. The same count was reported on Python 3.13.16 in `Management Pack/.venv-test` earlier.
- **Adapter definition:** dumped before and after the change. The same 3,439 paths. The only difference is the
  description of vCenter TLS Validation, which now carries the warning.
- **Build:** `tools/build/build.ps1` succeeded on Python 3.12.10 and produced `vCommunity_0.7.0.pak`. The build log has
  no SDK validation messages.
- **Static analysis:** `pip-audit` reports no known vulnerabilities. `bandit` reports one finding, the B105
  `"password"` field name, which is a false positive. The XML findings are suppressed with the SEC-05 reason. `ruff`
  reports 12 findings, listed under the open items.
- **Install and restart:** the pack installed on the test instance in 2 min 49 s. The adapter instance returned to
  `DATA_RECEIVING` after the restart.
- **Live validation** (`tools/validate/validate.ps1`): 16 pass, 4 warn, 0 fail. The warnings are the three Business
  Application checks, where no object carries the metric yet, and one 45-minute collection gap on 29 October, which is
  before this install. The log checks in the release steps are not done.

## Project rule for these items

[CONTRIBUTING.md](../../../CONTRIBUTING.md) says a broken behaviour is a GitHub issue with the label `bug`, and a plan or
an enhancement is a draft item on the To Do project. The bugs are issues #53 to #65, with their IDs in the titles. The
enhancements and plans are on the [To Do project](https://github.com/users/e1-rahabok/projects/1). Issues close when the
change is in a release and validated on the test instance. BUG-08 stays open until its callers are done.
