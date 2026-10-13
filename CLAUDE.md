# VCF Operations vCommunity Management Pack

A Python adapter (`Management Pack/app`) that collects extra properties and metrics from vCenter and publishes them onto the existing vCenter objects in VCF Operations under the `vCommunity|` key prefix.

## Documentation

Pages go in `docs/` by the rules in [docs/README.md](docs/README.md#where-a-new-page-goes). Add every new page to that index.

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
