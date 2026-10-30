# Handover: version 0.7.0, build, install and live validation

Temporary note for the Build Laptop. Delete this file once 0.7.0 is released and validated.

## Why

The engineering review (`docs/development-guide/engineering-review/2026-10-29-review.md`) found bugs, security gaps and repository gaps in
version 0.6.12. The fixes for 0.7.0 are written, and their unit tests pass on Python 3.13. They are not yet built,
installed or checked on the test instance. This note is for that part.

## Step 0: get the code (blocking)

The 0.7.0 changes are **not committed** yet. The Build Laptop cannot pick them up until they are.

- The author (Iwan) confirms the branch name, then commits and pushes. Proposed branch: `0.7.0-review-fixes`, from `main`.
- Commit message ends with the attribution line from the session instructions.
- Do not commit on `main`. Do not open a second branch.
- Once pushed: `git fetch origin && git checkout 0.7.0-review-fixes`.
- If the branch is not on origin yet, stop and ask Iwan. Do not rebuild from an older state.

## State

- Branch: `0.7.0-review-fixes` (once pushed). It is based on `main`.
- Manifest version: `0.7.0`. The build must produce `vCommunity_0.7.0.pak`.
- Unit tests: 476 passed on Python 3.13.16 (author's laptop). Not yet run on Python 3.12.
- Not run by the author: ruff, bandit, pip-audit, the SDK build validation, live validation. They are steps below.
- Issues: #53 to #65 are the fixed bugs. #60 (BUG-08) stays open on purpose. #66 is the Python version decision, still open.

## Steps on the Build Laptop

1. **Python 3.12.** The SDK build tool (`mp-build`, SDK 1.3.1) needs Python 3.9 to 3.12. `build.ps1` runs `python`, so
   `python --version` must print 3.12. If it prints 3.13, put a 3.12 install first on `PATH`, or fix the launcher, before
   building.
2. **Docker Desktop.** Start it and wait for "Engine running". Check with `docker info`.
3. **Registry.** `docker login ghcr.io`, with an account that can write `vcf-operations-vcommunity`.
4. **Test environment (Python 3.12).** From `Management Pack`:
   ```
   python -m venv .venv-312
   .venv-312\Scripts\python.exe -m pip install -r requirements.txt pytest ruff bandit pip-audit
   ```
   `.venv*` is git-ignored.
5. **Unit tests.** From `Management Pack`: `.venv-312\Scripts\python.exe -m pytest tests -q`. It also runs the docs
   link check. Expect 476 passed. Report any failure with its output.
6. **Lint (new in 0.7.0).** From `Management Pack`: `.venv-312\Scripts\python.exe -m ruff check app tests`. The rules are in
   `ruff.toml` at the repository root. The lint was not run by the author, so findings are expected. Fix the simple ones
   (unused imports, f-strings without placeholders, bare `except`). Report the rest with the file and line. Do not change
   behaviour to satisfy the linter.
7. **Security scan and audit.** From `Management Pack`:
   - `.venv-312\Scripts\python.exe -m bandit -r app -q`. The XML parser import in `utils/config_files.py` is marked
     `# nosec B314` on purpose. Report any other finding, and do not suppress one without a reason in the code.
   - `.venv-312\Scripts\python.exe -m pip_audit -r adapter_requirements.txt`. Report any advisory with its package.
8. **Build.** `pwsh tools/build/build.ps1`. It should end with a line naming `vCommunity_0.7.0.pak`. On failure, read
   `Management Pack/logs/build.log` and report the last 30 lines. The build runs the SDK validation of the adapter
   definition. A validation message is a finding, not a reason to skip it.
9. **Install.** Upload and install the pak, with `pwsh tools/install/install.ps1` if `.secrets/vcf-ops.xml` is on this
   laptop. Auto mode blocks that script in some sessions. If it is blocked, Iwan runs it in his own terminal.
10. **Restart.** `pwsh tools/restart/restart.ps1`. Adapter Instances often stop collecting after an upgrade, so this is
    required. Then wait one collection cycle, about 5 minutes.
11. **Live validation.** `pwsh tools/validate/validate.ps1`. It is read-only, and it reads the login from
    `.secrets/vcf-ops.xml`. Do not print that file. Exit 0 is a pass. Report every FAIL and WARN.

## Live checks specific to 0.7.0

Check these on the test instance after step 10. Report each one as seen, or not seen.

- **Default TLS mode.** Validate Connection works. The adapter log has the information line "Trust on First Use: the
  certificate of vCenter is not checked". It is information, not a warning, so **Collection Warnings must not fire** from it
  alone. If it fires, read its First Warning property and report it.
- **Refactored Windows guest collection.** On a Windows VM with Guest OS Service Monitoring and Windows Event Log Monitoring
  both Enabled, the service properties (`Guest OS|Services:...`), the OS properties (`Guest OS|Operating System|...`) and the
  event messages must still appear. Event messages now end with `]`. Report the count of each.
- **Content libraries.** The `Content Library` and `Library Item` objects must still appear. The log timing summary must
  list `collect_content_libraries`. The libraries are read every cycle (no cache) and that is expected.
- **Failure paths.** The log must not contain `Failed to read` for an object type unless vCenter really failed. The log
  must not contain a traceback from `collect_windows_events` or `vmService`.
- **Guest budget and timeout.** Only if a VM is known to hang, or if the log shows the timeout line. Otherwise report
  "not seen".
- **Pinned mode (only with Iwan's consent).** Changing the vCenter TLS setting on the test instance changes live behaviour.
  Ask first. If he agrees: set Pinned with the correct SHA-256 thumbprint, confirm the libraries still appear, then set the
  mode back.

## Report back

Reply with:

1. The branch and commit you built, and the Python version used.
2. The unit test result, with the count.
3. The ruff, bandit and pip-audit results, one line each, with any finding.
4. The build result and the pak name.
5. The validate result: pass, fail and warn counts, with each FAIL and WARN line.
6. The live checks above, one line each.

## After the report

- Iwan decides on the issues. Do not close #60 or #66. Close #53 to #59 and #61 to #65 only after live validation, with a comment that names the build.
- Tag `v0.7.0` only after Iwan approves the release (GOV-04). The repository has no changelog file on purpose: use GitHub release notes.
- Delete this file in the same change that closes the release.

## Do not

- Do not commit to `main`. Do not create issues. The issues and To Do items already exist.
- Do not print or commit `.secrets/`, `config.json` or any password.
- Do not use Claude in Chrome for screenshots. Use `tools/screenshot/screenshot.ps1` (see `CLAUDE.md`).
- Do not reintroduce `to-do.md`. Enhancements are on the To Do project: https://github.com/users/e1-rahabok/projects/1.
