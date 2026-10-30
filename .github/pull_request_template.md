## What changes, and why

<!-- One or two sentences. Link the issue (bug) or To Do item (enhancement). -->

## Checks

- [ ] `python -m pytest tests` passes in `Management Pack` (unit tests, and the docs link check)
- [ ] `python -m ruff check app tests` passes
- [ ] Docs updated for any user-visible change, and any new page is listed in `docs/README.md`
- [ ] `manifest.txt` version changed if this is a release
- [ ] Touches TLS, credentials or guest (VMware Tools) code: the security review in `docs/development-guide` is updated
- [ ] Live validation (`tools/validate/validate.ps1`) is run on the test instance after the next install, and the result is noted here
