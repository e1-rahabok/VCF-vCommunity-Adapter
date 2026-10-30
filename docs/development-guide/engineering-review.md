# Engineering Review: Code, Repository and VCF Operations 9 Fit

This page is the engineering review of the pack. It covers the adapter code, the tooling, the repository and the fit
with VCF Operations 9. Each finding has an ID, so it can be tracked, discussed and closed one at a time.

It reviews the state of the repository at version 0.6.12 (`Management Pack/manifest.txt`).

Where a finding was checked against the code, this page gives the file and line. Findings that were only read, and
not reproduced, say so.

---

## Verdict

The review is directionally right. The pack is a credible VCF Operations 9 management pack. Its design is careful:
the TLS modes, the input allow-lists and the failure isolation are strong. Its KPI math is tested with worked examples.

The gaps are in three places:

- the guest-operation code that runs inside Windows VMs,
- the automation around the code (there is no CI),
- a few documentation statements that do not match the code.

Two scores were given in the earlier reviews. The code scores 6.5 out of 10 (see [Summary](#summary)). The repository
and documentation score 8 out of 10. Both are right for their scope.

---

## Reviewer response and clarifications

I agree with the overall direction. The strongest findings are in the guest automation path, the TLS default
configuration and the lack of CI enforcement. A few items need more precise wording, so that they reflect the design
rather than sounding like a generic Python critique.

- **SEC-01.** The default mode is a deliberate trade-off for internal VMware environments. It is described as one in
  `utils/tls.py` and [TLS and Security Settings](../configuration-guide/tls-and-security.md). It is not an accidental bug,
  so I rate it Medium, not High. The stronger statement is: the default is operationally pragmatic but weak on
  security by design. The product should warn administrators that it accepts a certificate before verifying it.
  Users who need strict checks should opt in. The default itself does not change in 0.7.0.
- **SEC-02.** Agreed. The REST login in the library collector is not pinned in the way the guest transfer path is.
- **BUG-02.** Agreed that "the cache never works" is too strong. The cache is a module variable (`_cache` in
  `collectors/library/collectLibraryData.py`). The adapter runs as a new process for each cycle, so the cache never
  survives to the next cycle. The real issue is that the documentation implies a persistent hourly cache. Correct the
  documentation first. Only rework the code if a cross-cycle cache is needed.
- **GOV-02.** Agreed. This is a governance gap, not a code defect, and it is the top process item.
- **TST-01 and TST-02.** Agreed on the gaps. Say "not yet covered in the current environment", not "the code is
  untested".
- **DOC-02.** Agreed. Align the documentation with the design, or change the code, but not both in different directions.
- **GOV-04.** Corrected. Git tags do exist, up to `v0.6.10`. Versions 0.6.11 and 0.6.12 are not tagged. Do not add a
  changelog file: the project keeps no change history in the repository. Use GitHub release notes instead.
- **BUG-07.** Downgraded to Low. The code that can fail before `vm_name` is assigned is simple dictionary access.
- **BUG-09.** Only the first site (`adapter.py:157-158`) was found. The second site named in the earlier review
  (`adapter.py:349-352`) has no `return` inside a `finally`.
- **DOC-01.** The count is 12 metric pages, not 11. They are reachable through
  [Metrics](../reference/metrics/README.md), but the rule in `CLAUDE.md` says every page is listed in `docs/README.md`.

---

## How this review was done

Done:

- Read the adapter entry point, the collectors, the utilities and the guest-operation code.
- Read the packaging, the container image, the dependency pins and the tooling scripts.
- Read the GitHub configuration under `.github/`, and the root and pack `.gitignore` files.
- Checked each code finding against the file it names. Results are noted per finding.
- Ran the unit tests in the project virtual environment (`Management Pack/.venv-test`, Python 3.13.16):
  **433 passed**. The earlier review reported 422 on Python 3.12. That run was not repeated on 3.12.

Not done:

- **Live validation.** `tools/validate/validate.ps1` was not run. It tests the build installed on the instance, not
  this code.
- **Reproduction of the bugs.** Most bugs were found by reading the code. Reproduce each one before fixing it.
- **Concurrency tests.** The thread-safety findings need a test against a real vCenter.
- **Static analysis in this pass.** The earlier review's `ruff`, `bandit` and `pip-audit` results are not repeated here.
  The ruff count in TST-05 is not re-checked.

---

## Summary

- Code score: **6.5 / 10**. Repository and documentation score: **8 / 10**.
- The design is careful. The TLS modes, the input checks and the failure isolation are strong.
- The main risks are in the guest-operation code (Windows checks) and in the TLS default.
- The repository has no CI, no pull request template and no dependency bot. Lint is not enforced.
- Several known bugs sit in code that has no unit tests.

### Top priorities for 0.7.0

1. **BUG-01 (High).** A guest process that never exits blocks collection forever. Add a timeout and back-off.
2. **GOV-02 (High).** Add CI. Run the tests, lint and the docs link check on every pull request.
3. **SEC-02 (Medium).** Pin the library REST login to the same trust model as the rest of the pack.
4. **BUG-02 (Medium).** Correct the documentation of the library cache, which implies a persistent cache.
5. **SEC-01 (Medium).** Show a clear warning for the default TLS mode, in the UI and in the documentation.

### Scorecard

| Area | Score | Reason |
| :--- | :---: | :--- |
| Security | 6 | Good TLS design and input allow-lists. Insecure default. Pinned REST gap. |
| Reliability | 5 | Unbounded guest polling. Silent partial reads. Several wrong error paths. |
| Scalability | 6 | Bulk Suite API reads. Serial guest work per VM. One library call per item. |
| Concurrency | 6 | Good isolation. One shared connection across threads is unverified. |
| Maintainability | 6 | Clear layout. Long functions. Copy-pasted guest helpers. Mixed error styles. |
| Readability | 7 | Docstrings explain the "why". Naming and dead code are uneven. |
| Testing | 7 | 433 tests, strong on KPI math. Guest code and orchestration are untested. No CI. |
| Documentation | 8 | Very strong. Two known drifts. One index gap. |
| Repository hygiene | 5 | No CI, no PR template, no dependency bot, committed `.DS_Store`. |
| Dependencies | 8 | Runtime pins are exact. `pip-audit` clean for runtime (earlier review). Build tool has advisories. |

---

## Strengths

- **Design by object type.** Collectors, metrics and properties follow one pattern. See [Collectors](collectors.md).
- **Read the inventory, do not collect twice.** `utils/ops_inventory.py` and `utils/ops_stats.py` read what VCF
  Operations already holds, through the Suite API, in bulk.
- **Allow-lists for untrusted text.** Windows service names must match a strict pattern (`utils/guest_args.py:18`).
  A name with a quote is left out, not run.
- **Explicit TLS modes.** Three modes for vCenter and three for ESXi guest transfers. Unknown values are refused, not
  treated as "no check" (`utils/tls.py:86-96`, `utils/guest_http.py:67-84`).
- **Failure isolation.** A bad configuration file, or a failed object, does not stop the cycle. The problem is
  published on the vCenter object, and one alert fires (`utils/collection_health.py`).
- **Input validation for numeric settings.** Out-of-range values fall back to a default and log a warning
  (`metrics/cluster/cluster_risk_metrics.py:91-99`). Division guards are present where a divisor can be zero.
- **No dangerous primitives.** No `eval`, `exec`, `pickle`, `yaml.load` or `shell=True` in `Management Pack/app`.
- **Runtime dependencies are pinned.** `pyvmomi==8.0.3.0.1` is exact. The base image is versioned.
- **Documentation as a product surface.** It is organised by audience, and the contribution rules are clear
  ([CONTRIBUTING.md](../../CONTRIBUTING.md)). A link checker runs in the unit tests.
- **Security reporting.** [SECURITY.md](../../SECURITY.md) describes responsible disclosure.

---

## 1. Security

| ID | Severity | Where | Finding | Recommendation |
| :--- | :---: | :--- | :--- | :--- |
| SEC-01 | Medium | `utils/tls.py:118-120`, `adapter.py:376` | The default mode, Trust on First Use, connects without checking the certificate. The vCenter password is sent to whatever answers. A man-in-the-middle on the first connection can receive it. | Keep the default, which is a documented decision. Add a warning at adapter creation and in the configuration docs. Consider a pre-login thumbprint check as a stronger option. |
| SEC-02 | Medium | `collectors/library/collectLibraryData.py:83-97`, `:43`, `:46` | In Pinned mode, the thumbprint is checked on a separate TLS connection. The REST login then runs on a new connection with no pin. | Make the REST login use the same pinned trust model, or state the difference in the design. |
| SEC-03 | Medium | `utils/guest_http.py:52-53` | ESXi thumbprints are SHA-1 (40 hex). SHA-1 is not collision-resistant. | Accepted as a limit of what vCenter provides. Keep it documented. Do not change the trust model without a migration plan. |
| SEC-04 | Low | `utils/guest_http.py:208` | A pin mismatch is detected by searching the error text for `"ingerprint"`. The text depends on the urllib3 version. | Match the exception type or a stable error pattern. |
| SEC-05 | Low | `utils/config_files.py:20`, `adapter.py:102`, `adapter.py:195` | Configuration files use the standard XML parser. Bandit flags it (B314). The files are editable only by VCF Operations administrators. | Document the threat model. Keep the validation. |
| SEC-06 | Low | `tools/install/install.ps1`, `tools/restart/restart.ps1`, `tools/validate/review.ps1`, `tools/screenshot/screenshot.ps1` | Tooling uses `SkipCertificateCheck`. That suits internal lab use only. | Keep it for lab use. Say in the docs that it is lab-only. Do not use it in production steps. |
| SEC-07 | Low | `adapter.py:151` | `test()` logs the whole `ServiceContent` object at info level. Confirmed. | Log only the product name and version. |
| SEC-08 | Low | `.claude/settings.json:4` | The project allow-list lets an agent merge pull requests without a prompt (`Bash(gh pr merge *)`). Confirmed. | Remove the entry, or make the merge a deliberate human action. |
| SEC-09 | Info | `utils/guest_args.py` | Positive. Service names are allow-listed and tested. The command is built only from validated names. | Keep. Add a test for the curly-quote case, which the design already anticipates. |

### Good practice seen

- The Windows credential object is created for every VM. It is used only for Windows guests with VMware Tools running
  (`properties/vm/vmService.py:132`, `properties/vm/vmOSInformation.py:133`,
  `events/vm/collect_windows_event_logs.py:135`). Keep this rule.
- `presented_thumbprint` sends no credentials. It reads the certificate only (`utils/tls.py:123-143`).
- Guest transfers use a new session for each transfer. A pin cannot carry over to another host
  (`utils/guest_http.py:173-180`).

---

## 2. Reliability and correctness

| ID | Severity | Where | Finding | Recommendation |
| :--- | :---: | :--- | :--- | :--- |
| BUG-01 | High | `properties/vm/vmService.py:59`, `properties/vm/vmOSInformation.py:60`, `events/vm/collect_windows_event_logs.py:62` | Confirmed. The guest process polling loop is `while True` with no timeout or back-off. A hung process blocks collection forever. | Add a bounded timeout and a retry or back-off policy. Fail that VM cleanly with a collection warning. |
| BUG-02 | Medium | `collectors/library/collectLibraryData.py:100-118`, `commands.cfg` | Confirmed. The hourly cache is a module variable. Each cycle runs `adapter.py` as a new process, so the cache never survives to the next cycle. | Correct the documentation first (DOC-02). Move the cache to persisted state only if a cross-cycle cache is needed. |
| BUG-03 | Medium | `properties/vm/vmService.py:149`, `:155` | Confirmed. The service CSV is split with `line.split(',')`. A display name with a comma breaks the columns. | Parse the CSV correctly, for example with the `csv` module. |
| BUG-04 | Medium | `properties/vm/vmService.py:91-100`, `:148`, `:171` | `readOutput` returns `None` when the download is not HTTP 200. The next line calls `.strip()` on it. The outer code catches the error, but the `None` path is still a correctness bug. | Return an explicit failure object, or raise a typed exception, and handle it the same way everywhere. |
| BUG-05 | Medium | `events/vm/collect_windows_event_logs.py:139-146` | Confirmed by reading. If `createTempFile` fails, `tempFile` can be `None`. Line 143 calls `tempFile.split(...)` before the status check. The result is an `AttributeError`. | Check the temp file result before calling `.split()`. Reproduce it with a fault-injection test. |
| BUG-06 | Low | `events/vm/collect_windows_event_logs.py:181` | Confirmed. The message format is `"[WindowsEvent-{level} {message}"`. The bracket is never closed. | Close the bracket, and add a test for the message format. |
| BUG-07 | Low | `collectors/vm/collectVMData.py:127-177` | The `except` block uses `vm_name`, which is assigned at line 130. If a failure happens before that line on the first loop, `vm_name` is unbound. The path is unlikely. | Initialise `vm_name` before the `try`. |
| BUG-08 | Medium | `utils/ops_stats.py:151-156`, `:218-222`, `:229` | `read_latest_stats` and `read_latest_properties` log a failed batch and continue. They do not report it. The KPIs then run on incomplete data and look valid. | Return a structured failure, or count the partial read as a collection warning. |
| BUG-09 | Low | `adapter.py:157-158` | Confirmed. `return` inside `finally` silences any exception that is still raised, including `KeyboardInterrupt` and `SystemExit`. Ruff rule B012. | Move the return out of the `finally`. |
| BUG-10 | Low | `utils/vi_property_collector.py:74-83` | Confirmed. Any error returns `[]`, so a failed read looks like "no VMs". A bare `except:` hides errors from `view.Destroy()`. | Catch specific exceptions, log the failure, and return a typed failure result. |
| BUG-11 | Low | `adapter.py:186-191` | The event-log configuration is read without a `try`. A transient API error here discards the whole cycle. The other configuration reads handle errors. | Wrap this read in the same failure isolation used elsewhere. |
| BUG-12 | Low | `events/vm/getWindowsEventLogs.ps1:25-31` | `-ErrorAction SilentlyContinue` hides query errors. The query has a start time but no `-MaxEvents`. A noisy VM can return a very large event stream. | Log the error, set a cap, and add a safe timeout. |
| BUG-13 | Low | `utils/tls.py:146` | `explain_connect_error(exc, host, mode=None)` takes `mode`. Not yet verified whether the body uses it. | Check the body. Remove the parameter, or use it. |

### Good practice seen

- The collection health counter gives one alert, with the first warning, so a silent failure is visible.
- Each configuration file is independent. One bad file does not stop the others (`adapter.py:88-106`).
- Timing summaries are written at the end of each cycle (`adapter.py:115-140`).

---

## 3. Concurrency

| ID | Severity | Where | Finding | Recommendation |
| :--- | :---: | :--- | :--- | :--- |
| CON-01 | Medium | `adapter.py:239-311` | Eight jobs run in a thread pool of five. They share one pyVmomi `ServiceInstance`, its `content`, and one `CollectResult`. No statement-level race was found by reading, but the pattern should be tested under load. | Add a thread-safety test with a realistic vCenter workload. Decide whether one shared `ServiceInstance` is acceptable. |
| CON-02 | Low | `utils/guest_http.py:57-60`, `collectors/library/collectLibraryData.py:100`, `adapter.py:109` | Module-level mutable state: guest mode, thumbprint cache, warning set, and the timing map. Safe only while each process is single-threaded per collection. | Document the per-process lifecycle. Isolate the state if collection ever runs multi-threaded in one process. |
| CON-03 | Low | `adapter.py:313-330` | Futures are mapped to names with a long `if` chain. A dictionary is clearer and cannot drift. | Build the dictionary when the jobs are scheduled. |

---

## 4. Scalability and performance

| ID | Severity | Where | Finding | Recommendation |
| :--- | :---: | :--- | :--- | :--- |
| SCL-01 | Medium | `collectors/vm/collectVMData.py:156-165` | Each Windows VM gets three guest jobs, one after another. Each makes its own temporary folder, file transfers, process starts and reads. | Reduce guest work per VM. Skip jobs the VM does not need. Add a collection budget or a concurrency cap. |
| SCL-02 | Medium | `collectors/library/collectLibraryData.py:75-79` | One REST call for each library item. A library with thousands of items makes thousands of calls. | Use list endpoints that return the item data in bulk, or document the limit. |
| SCL-03 | Low | `events/vm/collect_windows_event_logs.py:170-185` | Every event is sent with `with_event`. There is no cap per VM. | Cap events per VM and per cycle. Log the count. See BUG-12. |
| SCL-04 | Info | `utils/ops_stats.py:20-22` | Positive. Stats and properties are read in batches of 1000. | Keep. Document the measured numbers. |
| SCL-05 | Info | `adapter.py`, `utils/tls.py`, `collectLibraryData.py` | One cycle logs in several times: pyVmomi, a separate TLS probe, the REST session and the Suite API token. | Acceptable. Document why they are separate, so they are not "optimised" by mistake. |

There is no performance benchmark. Collection time in large estates is not measured. This remains open.

---

## 5. Maintainability and readability

| ID | Severity | Where | Finding | Recommendation |
| :--- | :---: | :--- | :--- | :--- |
| MNT-01 | Medium | `adapter.py:161-352` | `collect()` is about 190 lines. It reads configuration, checks TLS, reads the Suite API, starts the thread pool and collects results. | Split it into steps: load configuration, resolve runtime context, run object jobs, finalise results. |
| MNT-02 | Medium | `collectors/vm/collectVMData.py:31-47`, `:80-106` | `collect_vm_data` takes 12 positional arguments. About 40 lines call `propertyPaths.append(...)` one at a time. | Group the settings in one context object or dataclass. |
| MNT-03 | Medium | `utils/*.py` | The error style changes from module to module: `None`, `[]`, `False`, a tuple, or an exception. | Choose one rule. Raise for a bug or a bad setting. Return a value only when the caller expects a fallback. |
| MNT-04 | Medium | `properties/vm/vmService.py`, `properties/vm/vmOSInformation.py`, `events/vm/collect_windows_event_logs.py` | The three files copy the same functions: `fileTransfer`, `executeProgram` and temp-file handling. | Factor these into one shared guest helper. The failure paths in BUG-03 to BUG-05 sit in this copied code. |
| MNT-05 | Low | `adapter.py:4`, `:6`; `properties/datastore/collect_ds_summary_properties.py:5` | Commented-out code and imports. | Remove them. Git keeps the history. |
| MNT-06 | Low | Ruff F401, F811, F541, E722, B110 | Four unused imports. A duplicate `vim` import (`collectVMData.py:27`). Eight f-strings without placeholders. Three bare `except` blocks. | Clean the lint issues, then enforce them in CI. |
| MNT-07 | Low | `collectors/vm/collectVMData.py` | A `TODO need to improve data collection` comment with no issue. | Turn it into a GitHub issue, or remove it. |
| MNT-08 | Low | `Management Pack/app/` file names | Mixed naming: `collectVMData.py`, `vmOSInformation.py`, `collect_ds_identifiers_properties.py`. Functions such as `getWinCredential` and `get_win_service_configFile`. | Pick one convention, and use it for new files. |
| MNT-09 | Info | `definition.py` (653 lines) | Long, but almost all of it is UI definition text. | Acceptable. Split by object type if it grows. |

### Good practice seen

- Names are descriptive. Docstrings explain the reason, not only the action (`utils/tls.py`, `utils/guest_http.py`).
- Constants are named. Metric keys and settings are in `constants/` and in each module.
- The KPI modules use small pure functions, which are easy to test (`metrics/cluster/cluster_risk_metrics.py`).

---

## 6. Testing

| ID | Severity | Finding | Recommendation |
| :--- | :---: | :--- | :--- |
| TST-01 | Info | Unit tests: 433 passed on Python 3.13.16 in `Management Pack/.venv-test`. Live validation was not run. | Run `tools/validate/validate.ps1` on the test instance after the next install. Run the tests on Python 3.12 as well (see below). |
| TST-02 | Medium | No unit tests for the guest code: `vmService.py`, `vmOSInformation.py`, `collect_windows_event_logs.py`. No tests for `adapter.collect()`, the VM loop, or the host, datastore and vCenter collection paths. | Add tests for the guest helper flows and for the collection orchestration. |
| TST-03 | Medium | The tests are not run automatically. | See GOV-02. |
| TST-04 | Low | No fault-injection tests: a hung process, a slow HTTP response, a partial read. | Add them with the guest helper (MNT-04). |
| TST-05 | Low | `ruff` found 22 issues at the rules F, E9 and B in the earlier review. Not re-checked. | Fix them, then enforce. |
| TST-06 | Info | KPI formulas are tested with worked examples. | Keep this practice. It is a strength. |

The pack's own documents disagree on the Python version. [CONTRIBUTING.md](../../CONTRIBUTING.md) says 3.12. The
earlier review says the SDK does not install on 3.13. The test virtual environment runs on 3.13.16 and the tests pass.
Decide which version is supported, then state it once and use it in CI.

---

## 7. Documentation

| ID | Severity | Finding | Recommendation |
| :--- | :---: | :--- | :--- |
| DOC-01 | Medium | `docs/README.md` does not list the 12 metric pages in `docs/reference/metrics/` directly. They are reachable from the metrics index. [CONTRIBUTING.md](../../CONTRIBUTING.md) says every page is listed in `docs/README.md`. | Add the missing pages to the docs index, or record the exception in `CONTRIBUTING.md`. |
| DOC-02 | Medium | [Template and Library Design](template-and-library-design.md) (about line 99) says the libraries are read once an hour and the last values are kept. The code does not (BUG-02). | Correct the documentation first. |
| DOC-03 | Low | Earlier reviews overlapped. This page now replaces them. | Keep this page as the single review. Close the items as they are done. |
| DOC-04 | Info | Positive. The docs are organised by audience. The contribution rules are clear. A link checker runs in the unit tests. | Keep. |

---

## 8. Repository hygiene and governance

| ID | Severity | Finding | Recommendation |
| :--- | :---: | :--- | :--- |
| GOV-01 | Low | Two `.DS_Store` files are tracked: `Management Pack/.DS_Store` and `Management Pack/app/.DS_Store`. The root `.gitignore` does not ignore them. Confirmed. | Remove them from Git. Add `.DS_Store` to the root `.gitignore`. |
| GOV-02 | High | No CI. The only file under `.github/` is the `ISSUE_TEMPLATE` folder. Tests, lint, the docs link check and the build are all manual. There is no pull request template. Confirmed. | Add a workflow for each pull request: `pytest`, `ruff`, `bandit`, `pip-audit` and the docs link check. Add a pull request template. |
| GOV-03 | Medium | No dependency bot, no CodeQL, no secret scanning, no `CODEOWNERS`. Confirmed: there is no `dependabot.yml`. | Enable Dependabot for pip and GitHub Actions. Enable secret scanning. Add `CODEOWNERS` for `Management Pack/app` and `tools/`. |
| GOV-04 | Low | Git tags exist, up to `v0.6.10`. Versions 0.6.11 and 0.6.12 are not tagged. | Tag each release from 0.7.0. Use GitHub release notes. Do not add a changelog file. |
| GOV-05 | Low | `Dockerfile:5-6` runs `pip3 install -r adapter_requirements.txt --upgrade`. Transitive dependencies are not pinned, and `--upgrade` changes the image on each build. | Pin transitive dependencies, or use a lock or hash-based install for the runtime image. |
| GOV-06 | Low | `vmware-aria-operations-integration-sdk==1.3.1` pulls `pillow 10.4.0` and `setuptools 78.1.1` at build time. `pip-audit` reports advisories for both. The base image may have known CVEs. | Track the upstream advisories. Update the dependency set before the release. |
| GOV-07 | Low | The root `.gitignore` does not ignore `.venv*`. `Management Pack/.gitignore` does. Confirmed. | Add `.venv*/` to the root `.gitignore`. |
| GOV-08 | Low | `Management Pack/content/**/.gitkeep` placeholder folders, some with no stated purpose. | Document each one in [Content Folder](content-folder.md), or remove it. |

---

## 9. Architecture notes

- **Each command in `commands.cfg` runs `adapter.py` as a new process**, with input and output files. Module-level state
  does not survive between cycles. Design every cache with that in mind (BUG-02, CON-02).
- **KPIs depend on the vCenter adapter.** The adapter reads the VCF Operations inventory through the Suite API. This
  keeps vCenter calls low. It also means KPIs depend on the vCenter adapter's own collection. Document that in the KPI pages.
- **The guest-operation path is the most fragile part of the pack.** It uses vSphere APIs and a PowerShell script. It
  needs the most tests and the strictest timeouts.
- **`adapter.py` is the maintenance hotspot.** It is the master registry of the adapter: object types, groups,
  properties, metrics, configuration parameters and the runtime orchestration. Its size is largely product-driven, but
  the two jobs should be separated over time (MNT-01).

---

## Prioritised plan

Status after the 0.7.0 change. "Done" means the code, tests and docs are in the working tree. It is not installed or
validated on the test instance yet, so each item still needs the live validation in the release steps.

### 0.7.0: done in the code

- [x] BUG-01: bounded guest polling, with the process stopped after 5 minutes. Issue #53.
- [x] BUG-02: the dead hourly cache is removed, and the documentation says the libraries are read in every cycle. Issue #54.
- [x] BUG-03, BUG-04, BUG-05, BUG-06: guest CSV parsing and error paths, with tests. Issues #55 to #58.
- [x] BUG-07: `vm_name` is set before the `try`. Issue #59.
- [x] BUG-08: the warning names how many resources have no value. Issue #60 stays open: the callers still publish totals from partial data.
- [x] BUG-09, BUG-10, BUG-11, BUG-12: returns out of `finally`, a failed vCenter read raises, the event list read is isolated, the event query is bounded. Issues #61 to #64.
- [x] BUG-13: the unused `mode` parameter is removed.
- [x] SEC-01: a warning in the setting's description, in the docs, and in the log at each connection (information level, so the alert does not fire).
- [x] SEC-02: the REST login is pinned during the handshake, and the separate probe is removed. Issue #65.
- [x] SEC-04: the mismatch text is a named constant, and a test checks it against the installed urllib3.
- [x] SEC-05: the XML parser is documented with its threat model, and marked for bandit.
- [x] SEC-07, SEC-08: the `ServiceContent` is no longer logged, and `gh pr merge` is removed from the project allow-list.
- [x] SEC-09: the curly-quote case already had a test (`tests/test_guest_args.py`).
- [x] GOV-01, GOV-07: the `.DS_Store` files are removed from Git, and `.DS_Store` and `.venv*/` are ignored.
- [x] GOV-02: CI workflow (`.github/workflows/ci.yml`), lint rules (`ruff.toml`), and a pull request template.
- [x] GOV-03: Dependabot for pip and GitHub Actions, and CODEOWNERS.
- [x] GOV-08: the placeholder folders are documented.
- [x] DOC-01: the 12 metric pages are listed in the docs index.
- [x] DOC-02: the library documentation matches the code.
- [x] DOC-03: this page is the single review.
- [x] MNT-01: `collect()` is split into `_collect_cycle` and `_run_object_jobs`.
- [x] MNT-02: the Windows guest settings are one `GuestSettings` object.
- [x] MNT-03: the error rule is written in [App Folder](app-folder.md#conventions).
- [x] MNT-04: the shared guest helper is `utils/guest_ops.py`.
- [x] MNT-05: the commented-out imports are removed.
- [x] MNT-07: the TODO is removed from the code, and the item is on the To Do project.
- [x] CON-03: the futures map to their job names with a dictionary.
- [x] SCL-01: a guest time budget of 30 minutes per cycle (the job count is open, below).
- [x] SCL-03: at most 100 events per VM per cycle, with a warning when more are found.
- [x] TST-02, TST-04: tests for the guest helpers, the collectors, the timeout and the failure paths (fakes, no VM needed).

### 0.7.0: open, and why

- [ ] BUG-08 (issue #60): callers do not skip the resources of a failed batch. There are 42 call sites in 19 files. Each one needs its own rule for a partial total.
- [ ] MNT-06, TST-05: ruff was not run in this change, because the package host was not reachable from the working environment. The CI workflow runs it on the first pull request. Expect to fix any findings it reports.
- [ ] GOV-04: tag `v0.7.0` when it is released. No changelog file: release notes on GitHub instead.
- [ ] SCL-02, SCL-01 (the job count), CON-01 (live test), GOV-05, GOV-06, GOV-03 (secret scanning and CodeQL), MNT-01 (the definition): on the To Do project, one line each.
- [ ] Python version (issue #66): the decision is open, so CI uses 3.12 for now.
- [ ] Live validation of 0.7.0 on the test instance (issue #2, `verify-live`).

### Verification done for this change

- Unit tests: 476 passed on Python 3.13.16 in `Management Pack/.venv-test`, with no skips. They include the docs link check.
- Adapter definition: dumped before and after the change. The same 3,439 paths. The only difference is the description of
  vCenter TLS Validation, which now carries the warning.
- The Integration SDK 1.3.1 build tool was not run. It needs Python 3.12 or older, and the package host was not reachable
  to install it. The build laptop runs `tools/build/build.ps1`, which runs `mp-build` and its validation.
- Python 3.12 unit tests were not run here, for the same reason.

### Project rule for these items

[CONTRIBUTING.md](../../CONTRIBUTING.md) says a broken behaviour is a GitHub issue with the label `bug`, and a plan or an
enhancement is a draft item on the To Do project. The bugs are issues #53 to #65, with their IDs in the titles. The
enhancements and plans are on the [To Do project](https://github.com/users/e1-rahabok/projects/1). Issues close when the
change is in a release and validated on the test instance, and BUG-08 stays open until its callers are done.

---

## Final assessment

The pack is careful and well explained. Its TLS design is thoughtful. Its input checks are strong. Its KPI math is
tested with worked examples.

The gaps are in the places that touch Windows guests, and in the automation around the code. Those areas need timeouts,
shared helpers, tests and CI. With those in place, the code score would move from about 6.5 to about 8.
