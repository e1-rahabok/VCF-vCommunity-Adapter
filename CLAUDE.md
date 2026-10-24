# VCF Operations vCommunity Management Pack

A Python adapter (`Management Pack/app`) that collects extra properties and metrics from vCenter and publishes them onto the existing vCenter objects in VCF Operations under the `vCommunity|` key prefix.

## Documentation

Pages go in `docs/` by the rules in [CONTRIBUTING.md](CONTRIBUTING.md#documentation). Add every new page to the contents in `docs/README.md`.

## Building

```
pwsh tools/build/build.ps1
```

Builds the `.pak` into `Management Pack/build` and pushes the adapter image to `ghcr.io/e1-rahabok/vcf-operations-vcommunity`. Don't call `mp-build` directly from a non-interactive shell: it crashes without a Windows console, and it waits on a prompt if `config.json` (gitignored) has no registry. The script handles both. Details: [tools/build/build.md](tools/build/build.md). All tools: [tools/README.md](tools/README.md).

## Installing on the test instance

```
pwsh tools/install/install.ps1
```

Uploads and installs the newest pak for the `manifest.txt` version (unsigned, signature checking ignored). Auto mode blocks this script, so ask the user to run it in their terminal, then run `pwsh tools/restart/restart.ps1` (the pack's Adapter Instances often stop collecting after an upgrade), wait one collection cycle, and run the live validation. Details: [tools/install/install.md](tools/install/install.md), [tools/restart/restart.md](tools/restart/restart.md).

## Screenshots

```
pwsh tools/screenshot/screenshot.ps1
```

Takes the docs' screenshots of the VCF Operations UI from the instance, as defined in `tools/screenshot/screenshots.json`, logging in like `install.ps1`. Use it to take or update screenshots, never Claude in Chrome. To add one, ask the user for an example of the part of the screen once, add an entry, and run it with `-Name` and `-SaveSteps` until it matches. Details: [tools/screenshot/screenshot.md](tools/screenshot/screenshot.md).

## Testing

Run both layers after any change under `Management Pack/app`, and report the results of each.

1. **Unit tests** (fakes, no live system). From the `Management Pack` folder:

   ```
   python -m pytest tests
   ```

2. **Live validation** (read-only, against the VCF Operations test instance):

   ```
   pwsh tools/validate/validate.ps1
   ```

   - Reads the URL and login from `.secrets/vcf-ops.xml` (gitignored, never commit or print it).
   - Exits 0 on pass, 1 on any FAIL. WARN lines are worth mentioning but do not fail the run.
   - It tests the build **installed on the instance**, not the code in this repo. A code change is only covered once that build has been installed there; say so plainly if it has not.

If a layer cannot be run (for example Python is not installed), say that instead of skipping it silently.
