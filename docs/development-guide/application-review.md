# Application Review: Security, Reliability, Maintainability

This page is an in-depth review of the adapter code, the tooling, and the repository. It follows the same
structure as the other engineering reviews in this folder. Each finding has an ID, so it can be tracked, discussed,
and closed one by one.

It reviews the state of the repository at version 0.6.10 (`Management Pack/manifest.txt`).

The earlier, more general review is [Repository Review](repository-review.md). This page goes deeper into the code.
Where the two overlap, this page gives the evidence: file and line.

---

## How this review was done

- Read the adapter entry point, the collectors, the utilities, and the guest-operation code.
- Read the packaging, the container image, the dependency pins, and the tooling scripts.
- Ran the unit test suite. Python 3.12, pytest 9.2.0: **422 passed**.
- Ran `ruff` (pyflakes, pycodestyle, bugbear rules) on `Management Pack/app`.
- Ran `bandit` on `Management Pack/app`.
- Ran `pip-audit` on `Management Pack/adapter_requirements.txt` (runtime) and `requirements.txt` (build).

Not done:

- **Live validation.** No test instance was available. `tools/validate/validate.ps1` was not run.
- **Reproduction of the bugs.** Most bugs below were found by reading the code. Each one says so. Reproduce them
  before fixing.
- **Concurrency tests.** The thread-safety findings need a test against a real vCenter.

---

## Summary

- Overall score: **6.5 / 10**.
- The design is careful. The TLS modes, the input checks, and the failure isolation are strong.
- The main risks are in the guest-operation code (Windows checks) and in the TLS defaults.
- The repository has no CI. Lint is not enforced. Several known bugs sit in code that has no unit tests.

### Top priorities

1. **BUG-01 (High).** A guest process that never exits blocks the collection forever. Fix the polling loop.
2. **SEC-01 (High).** The default TLS mode sends the vCenter password before the server is verified.
   Document it clearly. Show a warning. Consider a pre-login thumbprint check.
3. **SEC-02 (Medium).** In Pinned mode, the library REST login is not pinned. Fix it.
4. **BUG-02 (Medium).** The hourly library cache never works. The code runs in a new process every cycle.
   Fix the code or the documentation.
5. **GOV-02 (Medium).** Add CI. Run the tests, the lint, and the docs link check on every pull request.

### Scorecard

| Area | Score | Reason |
| :--- | :---: | :--- |
| Security | 6 | Good TLS design and input allow-lists. Insecure default. Pinned REST gap. |
| Reliability | 5 | Unbounded guest polling. Silent partial reads. Several wrong error paths. |
| Scalability | 6 | Bulk Suite API reads. Serial guest work per VM. N+1 library reads. |
| Concurrency | 6 | Good isolation. One shared connection across threads is unverified. |
| Maintainability | 6 | Clear layout. Long functions. Copy-pasted guest helpers. Mixed error styles. |
| Readability | 7 | Good docstrings that explain the "why". Naming and dead code are uneven. |
| Testing | 7 | 422 tests, strong on KPI math. Guest code and orchestration are untested. No CI. |
| Documentation | 8 | Very strong. Two known drifts. One index gap. |
| Repository hygiene | 5 | No CI, no PR template, no tags, committed `.DS_Store`, no dependency bot. |
| Dependencies | 8 | Runtime pins are exact. `pip-audit` clean for runtime. Build tool has advisories. |

---

## Strengths

- **Design by object type.** Collectors, metrics, and properties follow one pattern.
  See [Collectors](collectors.md).
- **Read the inventory, do not collect twice.** `utils/ops_inventory.py` and `utils/ops_stats.py` read what VCF
  Operations already holds, through the Suite API, in bulk.
- **Allow-lists for untrusted text.** Windows service names must match a strict pattern
  (`utils/guest_args.py:18`). A name with a quote is left out, not run.
- **Explicit TLS modes.** Three modes for vCenter. Three modes for ESXi guest transfers. Unknown values are refused,
  not treated as "no check" (`utils/tls.py:86-96`, `utils/guest_http.py:67-84`).
- **Failure isolation.** A bad configuration file, or a failed object, does not stop the cycle. The problem is
  published on the vCenter object, and one alert fires (`utils/collection_health.py`).
- **Input validation for numeric settings.** Out-of-range values fall back to a default and log a warning
  (`metrics/cluster/cluster_risk_metrics.py:91-99`). Division guards are present where a divisor can be zero.
- **No dangerous primitives.** No `eval`, `exec`, `pickle`, `yaml.load`, or `shell=True` in `Management Pack/app`.
- **Runtime dependencies are pinned.** `pyvmomi==8.0.3.0.1` is exact. The base image is versioned.

---

## 1. Security

### Findings

| ID | Severity | Where | Finding | Recommendation |
| :--- | :---: | :--- | :--- | :--- |
| SEC-01 | High | `utils/tls.py:118-120`, `adapter.py:376` | The default mode, Trust on First Use, connects without checking the certificate. The vCenter password is sent to whatever answers. A man-in-the-middle can read the service account password, on every collection. | Keep the default for compatibility, but make it visible. Show a warning in Validate Connection and in the log. In the documentation, recommend Pinned or Enabled for production. Consider comparing the presented certificate with the thumbprint recorded on the vCenter object before the login, and warning or refusing on a change, according to the mode. |
| SEC-02 | Medium | `collectors/library/collectLibraryData.py:83-97`, `:43`, `:46` | In Pinned mode, the thumbprint is checked on a separate TLS connection. The REST login then runs on a new connection with `verify=False`. The login is not pinned. An attacker who answers the check with the right certificate, and then the login with another one, gets the password. | Pin the REST session itself, with the same `assert_fingerprint` approach as `utils/guest_http.py:160-170`. Remove the separate probe. |
| SEC-03 | Medium | `utils/guest_http.py:52-53` | ESXi thumbprints are SHA-1 (40 hex). Pinning uses them. SHA-1 is not collision-resistant. | Accepted as a limit of what vCenter provides. Keep it documented as a residual risk. Say so in [TLS and Security Settings](../configuration-guide/tls-and-security.md). |
| SEC-04 | Low | `utils/guest_http.py:208` | A pin mismatch is detected by searching the error text for `"ingerprint"`. The text depends on the urllib3 version. | Match the exception type or a stable attribute, and add a unit test with the pinned version. |
| SEC-05 | Low | `utils/config_files.py:20`, `adapter.py:102`, `adapter.py:195` | Configuration files are parsed with the standard XML parser. Bandit flags it (B314). The files are editable only by VCF Operations users with configuration rights. | Use `defusedxml`, or document the trust assumption. Expat in current Python versions limits entity expansion. Confirm this on the target Python version. |
| SEC-06 | Low | `tools/install/install.ps1:74,88,121`, `tools/restart/restart.ps1:55`, `tools/validate/validate.ps1:82`, `tools/screenshot/screenshot.ps1:75` | Tooling uses `SkipCertificateCheck`. The screenshot tool puts the password in an environment variable. The installer uses `ignoreSignatureChecking=true`. | These are operator tools for a lab instance. Document the risk in each `.md` file. Remove the environment variable in favour of a secure string where possible. |
| SEC-07 | Low | `adapter.py:151` | `test()` logs the whole `ServiceContent` object at info level. | Log only the product name and version. |
| SEC-08 | Low | `.claude/settings.json:4` | The project allow-list lets an agent merge pull requests without a prompt (`Bash(gh pr merge *)`). | Remove the entry, or make the merge a deliberate human step. |
| SEC-09 | Info | `utils/guest_args.py` | Positive. Service names are allow-listed and tested. The command is built only from validated names. | Keep. Add a test for the curly-quote case, which the docstring mentions. |

### Good practice seen

- The Windows credential object is created for every VM. It is used only for Windows guests with VMware Tools
  running (`properties/vm/vmService.py:132`, `properties/vm/vmOSInformation.py:133`,
  `events/vm/collect_windows_event_logs.py:135`). Keep this rule.
- `presented_thumbprint` sends no credentials. It reads the certificate only (`utils/tls.py:123-143`).
- Guest transfers use a new session for each transfer. A pin cannot carry over to another host (`utils/guest_http.py:173-180`).

---

## 2. Reliability and correctness

### Findings

| ID | Severity | Where | Finding | Recommendation |
| :--- | :---: | :--- | :--- | :--- |
| BUG-01 | High | `properties/vm/vmService.py:59-63`, `properties/vm/vmOSInformation.py:60`, `events/vm/collect_windows_event_logs.py:62` | The guest process polling loop is `while True` with no timeout and no sleep. If PowerShell hangs, the thread never returns. `as_completed` in `adapter.py:313` waits forever, and the whole cycle never ends. Without a sleep, the loop also calls the vSphere API as fast as it can. | Add a deadline (for example 300 seconds). Add a `time.sleep` between polls, with a short back-off. On timeout, kill the guest process and log the VM name. Put the loop in one shared helper (see MNT-06). |
| BUG-02 | Medium | `collectors/library/collectLibraryData.py:100-118`, `commands.cfg` | The hourly cache is a module variable. The Cloud Proxy runs `adapter.py collect <in> <out>` as a new process for every cycle. The cache is always empty at the start, so the library is read every cycle. The design says once an hour (`docs/development-guide/template-and-library-design.md:99`). | Store the read time and the data in a file in a writable folder, or as properties on the library objects, and read them back. Or change the documentation and say the read runs every cycle. Confirm in the adapter log: one REST login per cycle. |
| BUG-03 | Medium | `properties/vm/vmService.py:149`, `:155` | The service CSV is split on commas with `line.split(',')`. A display name with a comma (for example `"Microsoft Office Click-to-Run, Service"`) shifts the columns. The event-log collector uses the `csv` module, so the two disagree. | Use `csv.reader`, as `collect_windows_event_logs.py:153` does. Add a unit test with a quoted comma. |
| BUG-04 | Medium | `properties/vm/vmService.py:91-100`, `:148`, `:171` | `readOutput` returns `None` when the download is not HTTP 200. The next line calls `.strip()` on it. The error is caught by the outer handler, which logs "Failed to create temporary directory". The message is wrong and the real cause is hidden. | Raise a specific error in `readOutput`. Log the real reason. Fix the message at line 171. |
| BUG-05 | Medium | `events/vm/collect_windows_event_logs.py:139-146` | If `createTempFile` fails, `tempFile` is `None`. Line 143 calls `tempFile.split(...)` before the status check. The error is `AttributeError`, logged as "An error occurred during Windows Event Log collection". | Check `tempFileStatus` before line 143. Log the real reason. |
| BUG-06 | Low | `events/vm/collect_windows_event_logs.py:181` | The message format is `"[WindowsEvent-{level} {message}"`. The opening bracket is never closed. | Close the bracket, and add a test for the text that is shown on the object. |
| BUG-07 | Medium | `collectors/vm/collectVMData.py:127-177` | The `except` block uses `vm_name`. It is assigned at line 130. If something fails before line 130 on the first loop, `vm_name` is unbound. The `UnboundLocalError` leaves the loop, and the remaining VMs of this cycle are lost. (Found by reading. Not reproduced.) | Set `vm_name = "Unknown"` before the `try`. Add a test where `propSet` is `None`. |
| BUG-08 | Medium | `utils/ops_stats.py:151-156`, `:218-222`, `:229` | `read_latest_stats` and `read_latest_properties` log a failed batch and continue. They do not report the failure. The KPIs then run on a partial inventory with no signal. `read_latest_timestamps` (line 68-69) returns `None` instead. The two contracts differ. | Pick one contract for all reads. Return the failed ids, as `read_stat_history` does, and let the caller decide. Count a failed batch in the collection health warnings. |
| BUG-09 | Low | `adapter.py:157-158`, `:349-352` | `return` inside `finally` silences any exception that is still raised, including `KeyboardInterrupt` and `SystemExit`. Ruff rule B012. | Move the `return` after the `finally` block. |
| BUG-10 | Low | `utils/vi_property_collector.py:74-83` | Any error returns `[]`. The VM property read then looks like "no VMs". A bare `except:` hides the error from `view.Destroy()`. The first handler also calls `view.Destroy()` without a guard. | Re-raise after logging, or return a result that the caller must check. Replace the bare `except` with `except Exception`. |
| BUG-11 | Low | `adapter.py:186-191` | The event-log configuration is read without a `try`. A transient API error here discards the whole cycle. The other configuration reads (`get_config_file_data`) handle it. | Use the same helper as the other files. |
| BUG-12 | Low | `events/vm/getWindowsEventLogs.ps1:25-31` | `-ErrorAction SilentlyContinue` hides query errors. The query is limited by start time only, with no `-MaxEvents`. A noisy VM can return a very large list in one cycle. | Use `-ErrorAction Stop` in the `try` and log the error. Add a maximum per VM and per cycle, and document it. |
| BUG-13 | Low | `utils/tls.py:146` | `explain_connect_error(exc, host, mode=None)` never uses `mode`. | Remove the parameter, or use it. |

### Good practice seen

- The collection health counter gives one alert, with the first warning, so a silent failure is visible.
- Each file of configuration is independent. One bad file does not stop the others (`adapter.py:88-106`).
- Timing summaries are written at the end of each cycle (`adapter.py:115-140`).

---

## 3. Concurrency

| ID | Severity | Where | Finding | Recommendation |
| :--- | :---: | :--- | :--- | :--- |
| CON-01 | Medium | `adapter.py:239-311` | Eight jobs run in a thread pool of five. They share one pyVmomi `ServiceInstance` and its `content`, and one `CollectResult`. This review found no statement that a pyVmomi connection is safe to share between threads. Treat it as unverified. (Not reproduced.) | Test under load against a real vCenter, with the `vim` calls logged. If it fails or is unclear, give each worker its own connection, or serialise vSphere calls behind a lock. |
| CON-02 | Low | `utils/guest_http.py:57-60`, `collectors/library/collectLibraryData.py:100`, `adapter.py:109` | Module-level mutable state: the guest mode, the thumbprint cache, the warning set, the library cache, and the timings. It works only because each cycle is a new process. | Put the state in an object created per cycle, and pass it in. This also makes the code testable. |
| CON-03 | Low | `adapter.py:313-330` | The results of the futures are mapped to names with a long `if` chain. A dictionary from future to name is clearer and cannot drift. | Build a dictionary when each future is submitted. |

---

## 4. Scalability and performance

| ID | Severity | Where | Finding | Recommendation |
| :--- | :---: | :--- | :--- | :--- |
| SCL-01 | Medium | `collectors/vm/collectVMData.py:156-165` | Each Windows VM gets three separate guest jobs, one after another. Each job makes its own temporary folder, file transfers, process start, polling, and cleanup. The cost grows with the VM count. There is no limit on how many VMs run at once, and no budget per cycle. | Combine the three jobs into one script call per VM, or run a small, bounded number of VMs in parallel. Add a per-cycle time budget, and log the VMs skipped when the budget ends. |
| SCL-02 | Medium | `collectors/library/collectLibraryData.py:75-79` | One REST call for each library item. A library with thousands of items makes thousands of calls. | Use the list endpoints that return details, or read the items in parallel with a limit. Measure the time first. |
| SCL-03 | Low | `events/vm/collect_windows_event_logs.py:170-185` | Every event is sent with `with_event`. There is no cap per VM. | Cap the events per VM and per cycle, with a count in the log. See BUG-12. |
| SCL-04 | Info | `utils/ops_stats.py:20-22` | Positive. Stats and properties are read in batches of 1000. History is read in smaller batches. | Keep. Document the numbers that were measured. |
| SCL-05 | Info | `adapter.py`, `utils/tls.py`, `collectLibraryData.py` | One cycle logs in several times: pyVmomi, a separate TLS probe, the REST session, and the Suite API token. | Acceptable. Count the logins in the test instance. Pinning would let the probe go (SEC-02). |

There is no performance benchmark. The earlier review also noted this. It remains open.

---

## 5. Maintainability and readability

| ID | Severity | Where | Finding | Recommendation |
| :--- | :---: | :--- | :--- | :--- |
| MNT-01 | Medium | `adapter.py:161-352` | `collect()` is about 190 lines. It reads configuration, checks TLS, reads the Suite API, starts the thread pool, and collects results. | Split it into steps: read settings, read configuration, start the jobs, collect results. Each step is testable. |
| MNT-02 | Medium | `collectors/vm/collectVMData.py:31-47`, `:80-106` | `collect_vm_data` takes 12 positional arguments. About 40 lines call `propertyPaths.append(...)` one by one. Settings are compared with strings such as `"Enabled"`. | Pass a settings object. Write the property paths as one list literal. Use constants for the setting values. |
| MNT-03 | Medium | `utils/*.py` | The error style changes from module to module: `None`, `[]`, `False`, a tuple, or an exception. | Choose one rule. Raise for a bug or a bad setting. Return a value with an explicit "no data" for a missing object. Write it in [Supporting Code](supporting-code.md). |
| MNT-04 | Medium | `properties/vm/vmService.py`, `properties/vm/vmOSInformation.py`, `events/vm/collect_windows_event_logs.py` | The three files copy the same functions: `fileTransfer`, `executeProgram`, `createTempFile`, and the cleanup. Each copy has its own version of BUG-01. | Move the shared guest code into `utils/guest_jobs.py`, with one timeout and one polling loop. |
| MNT-05 | Low | `adapter.py:4`, `:6`; `properties/datastore/collect_ds_summary_properties.py:5` | Commented-out code and imports. | Remove them. Git keeps the history. |
| MNT-06 | Low | Ruff F401, F811, F541, E722, B110 | Four unused imports. A duplicate `vim` import (`collectVMData.py:27`). Eight f-strings without placeholders. Three bare `except` blocks that swallow errors (`vmOSInformation.py:192`, `vmService.py:178`, `collect_windows_event_logs.py:206`). | Fix them. Add `ruff` to CI (see GOV-02). |
| MNT-07 | Low | `collectors/vm/collectVMData.py` | A `TODO need to improve data collection` comment with no issue. | Turn it into an issue, or remove it. |
| MNT-08 | Low | `Management Pack/app/` file names | Mixed naming. Files: `collectVMData.py`, `vmOSInformation.py`, `collect_ds_identifiers_properties.py`. Functions: `getWinCredential`, `get_win_service_configFile`. | Choose snake_case for new files. Rename old files only with a reason, because the imports and the docs use the paths. |
| MNT-09 | Info | `definition.py` (653 lines) | Long, but almost all of it is UI definition text. | Acceptable. Consider splitting by object type when it grows. |

### Good practice seen

- Names are descriptive. Docstrings explain the reason, not only the action (`utils/tls.py`, `utils/guest_http.py`).
- Constants are named. Metric keys and settings are in `constants/` and in each module.
- The KPI modules use small pure functions, which are easy to test (`metrics/cluster/cluster_risk_metrics.py`).

---

## 6. Testing

| ID | Severity | Finding | Recommendation |
| :--- | :---: | :--- | :--- |
| TST-01 | Info | Unit tests: 422 passed on Python 3.12 (this review). Live validation was not run. | Run `tools/validate/validate.ps1` on the test instance, after the next install. |
| TST-02 | Medium | No unit tests for the guest code: `vmService.py`, `vmOSInformation.py`, `collect_windows_event_logs.py`. No tests for `adapter.collect()`, the VM loop, or the host, datastore, and vCenter collectors. Some tests only import the module (`tests/test_submodule_imports.py`). | Start with fakes for `fileManager` and `processManager`. Test the CSV parsing (BUG-03), the bad download (BUG-04), the event-log failure (BUG-05), and the timeout (BUG-01). |
| TST-03 | Medium | The tests are not run automatically. | See GOV-02. |
| TST-04 | Low | No fault-injection tests: a hung process, a slow HTTP response, a partial read. | Add them with the guest helper (MNT-04). |
| TST-05 | Low | `ruff` finds 22 issues at the rules F, E9, B. | Fix them, then enforce. |
| TST-06 | Info | KPI formulas are tested with worked examples (315 test functions). | Keep this practice. It is a strength. |

The local environment needs Python 3.12. The SDK does not install on Python 3.13
(`vmware-aria-operations-integration-sdk==1.3.1` requires below 3.13). [CONTRIBUTING.md](../../CONTRIBUTING.md) says
3.12. CI must use 3.12 as well.

---

## 7. Documentation

| ID | Severity | Finding | Recommendation |
| :--- | :---: | :--- | :--- |
| DOC-01 | Medium | `docs/README.md` does not list 11 metric pages in `docs/reference/metrics/`, nor [Repository Review](repository-review.md). `CLAUDE.md` and `CONTRIBUTING.md` say every page must be listed. This page is listed. | Add the missing pages to the contents. Add a test that fails when a page is not listed. |
| DOC-02 | Medium | `docs/development-guide/template-and-library-design.md:99` says the libraries are read once an hour and the last values are kept. The code does not (BUG-02). | Fix the code or the page. The page must match the behaviour. |
| DOC-03 | Low | Two reviews now overlap: [Repository Review](repository-review.md) and this page. | Keep both, with the scope stated at the top of each. Link them. Close the items when they are done. |
| DOC-04 | Info | Positive. The docs are organised by audience. The contribution rules are clear. A link checker runs in the unit tests. | Keep. |

---

## 8. Repository hygiene and governance

| ID | Severity | Finding | Recommendation |
| :--- | :---: | :--- | :--- |
| GOV-01 | Low | Two `.DS_Store` files are tracked: `Management Pack/.DS_Store` and `Management Pack/app/.DS_Store`. The root `.gitignore` does not ignore them. | Remove them from Git. Add `.DS_Store` to the root `.gitignore`. |
| GOV-02 | High | No CI. No workflow in `.github/`. Tests, lint, the docs link check, and the build are all manual. The pull request template is missing too. | Add a workflow for each pull request: `pytest` on Python 3.12, `ruff`, `tools/check-docs/check_links.py`, and a check that the manifest version matches the release. Add a pull request template from the repository's own checklist. |
| GOV-03 | Medium | No dependency bot, no CodeQL, no secret scanning, no `CODEOWNERS`. | Enable Dependabot for pip and GitHub Actions. Enable secret scanning. Add `CODEOWNERS` for `Management Pack/app/utils/tls.py` and `guest_http.py`. |
| GOV-04 | Low | No git tags. The version is only in `manifest.txt`. The release commits say "Release 0.6.10". | Tag each release. Add a changelog file. |
| GOV-05 | Low | `Dockerfile:5-6` runs `pip3 install -r adapter_requirements.txt --upgrade`. Transitive dependencies are not pinned, and `--upgrade` changes the image on each build. | Pin all transitive packages (a lock file or hashes). Remove `--upgrade`. |
| GOV-06 | Low | Build-time dependencies: `vmware-aria-operations-integration-sdk==1.3.1` pulls `pillow 10.4.0` and `setuptools 78.1.1`. `pip-audit` reports advisories for both. The runtime container is clean: `pip-audit` on `adapter_requirements.txt` found no known vulnerabilities. | Upgrade the build tooling when the SDK allows it. Keep the build machine patched. |
| GOV-07 | Low | The root `.gitignore` does not ignore `.venv*`. `Management Pack/.gitignore` does. | Add `.venv*/` to the root `.gitignore`. |
| GOV-08 | Low | `Management Pack/content/**/.gitkeep` placeholder folders, some with no purpose stated. | Document each one in [Content Folder](content-folder.md), or remove it. |

---

## 9. Architecture notes

- Each command in `commands.cfg` runs `adapter.py` as a new process, with input and output files. Module-level state
  does not survive between cycles. Design every cache with that in mind (BUG-02, CON-02).
- The adapter reads the VCF Operations inventory through the Suite API. This keeps vCenter calls low. It also means
  KPIs depend on the vCenter adapter's own collection. Document that dependency in the KPI pages.
- The guest-operation path uses vSphere APIs and a PowerShell script. It is the most fragile part of the pack. It
  needs the most tests and the strictest timeouts.

---

## Prioritised plan

### Now (before the next release)

- [ ] BUG-01: timeout and back-off in the guest polling loop.
- [ ] SEC-02: pin the library REST session. Remove the separate probe.
- [ ] BUG-02: fix the library cache, or correct DOC-02.
- [ ] DOC-01: list the missing pages in `docs/README.md`.
- [ ] GOV-02: add a CI workflow with tests, lint, and the docs link check.

### Next

- [ ] BUG-03, BUG-04, BUG-05: fix the guest parsing and error paths. Add tests (TST-02).
- [ ] BUG-07: `vm_name` before the `try`. Add a test.
- [ ] BUG-08: one contract for failed reads. Count them in the health warnings.
- [ ] SEC-01: visible warning for the default TLS mode. Documentation for production.
- [ ] MNT-04: one shared guest helper.
- [ ] CON-01: test the thread safety of one connection under load. Decide.
- [ ] GOV-01, GOV-03, GOV-04: hygiene, bots, tags.

### Later

- [ ] MNT-01, MNT-02, MNT-03: split `collect()`, group the settings, one error style.
- [ ] SCL-01: fewer guest jobs per VM, and a time budget per cycle.
- [ ] SCL-02: fewer library item calls.
- [ ] BUG-12, SCL-03: event-log limits.
- [ ] MNT-06: lint clean, then enforce it.
- [ ] Consolidate with [Repository Review](repository-review.md) (DOC-03).

---

## Project rule for these items

[CONTRIBUTING.md](../../CONTRIBUTING.md) says that a broken behaviour is an issue, and a plan is a To Do item.
Open a GitHub issue with the `bug` label for each BUG item. Use the ID in the title, for example
`BUG-01: guest process polling has no timeout`. Link the issue back here when it is open.

---

## Final assessment

The pack is careful and well explained. Its TLS design is thoughtful. Its input checks are strong. Its KPI math is
tested with worked examples.

The gaps are in the places that touch Windows guests and in the automation around the code. Those areas need timeouts,
shared helpers, tests, and CI. With those in place, the score would move from about 6.5 to about 8.
