# Build Script

`build.ps1` builds the management pack's `.pak` file, with no prompts. It runs `mp-build` from the [VCF Operations Integration SDK](https://github.com/vmware/vmware-aria-operations-integration-sdk), in a way that also works from a script, CI or Claude Code.

To install the result on the test instance, see [Install Script](../install/install.md).

## What it produces

| Output | Where |
| :--- | :--- |
| The `.pak` file, such as `vCommunity_0.4.2.pak` | `Management Pack/build/` (gitignored) |
| The adapter's container image | Pushed to `ghcr.io/e1-rahabok/vcf-operations-vcommunity`, tagged `<version>_<timestamp>`, such as `0.4.2_1792737482.229203` |

The pak does not contain the adapter's code. It names the image to run, and each Cloud Proxy pulls that image from the registry. So **every build pushes an image**, and a pak only works while its image is in the registry. See [How It Works](../../docs/installation-guide/how-it-works.md).

The version comes from `Management Pack/manifest.txt`.

## Requirements

- PowerShell 7 (`pwsh`).
- Python, with the Integration SDK 1.3 or later: `pip install vmware-aria-operations-integration-sdk`.
- Docker Desktop, running. The SDK builds the image locally, starting from its own base image `base-adapter:python-1.2.0` (see `Management Pack/Dockerfile`).
- Push access to the registry: `docker login ghcr.io` with a GitHub account that can write the `vcf-operations-vcommunity` package.

## Running it

From the repo root:

```powershell
pwsh tools/build/build.ps1
```

| Parameter | Default | Meaning |
| :--- | :--- | :--- |
| `-Registry` | `ghcr.io/e1-rahabok/vcf-operations-vcommunity` | Where the image is pushed, and where VCF Operations pulls it from. |
| `-TimeoutMinutes` | `15` | `mp-build` is stopped after this long. |

A build takes under a minute when the base image is already built. The first build on a machine also builds the base image, which adds about 2 minutes.

The script ends with the path of the pak, such as `Built …\Management Pack\build\vCommunity_0.4.2.pak (424 KB)`, and exits `0`. It exits `1` when no pak for the manifest version was made.

## What it does

1. **Checks Docker.** It stops at once if the Docker engine does not answer, instead of letting `mp-build` fail halfway through.
2. **Sets the registry.** `mp-build` reads the registry from `Management Pack/config.json`, and asks for one when it is empty. That file is gitignored, so a fresh clone has none. The script writes `-Registry` into it.
3. **Runs `mp-build`**, through `mp_build_headless.py`, with no keyboard input. `mp-build` then:
   1. builds the adapter image,
   2. starts it, and checks that the adapter answers and that its `describe.xml` is valid,
   3. tags the image and pushes it,
   4. assembles the pak.
4. **Checks for the pak.** It looks for a pak for the manifest version, written during this run. It does not rely on `mp-build`'s exit code, which is not reliable.

`mp-build` logs every step in `Management Pack/logs/build.log`. Look there first when a build fails.

## Why a wrapper

`mp-build` prints its progress with `prompt_toolkit`, which on Windows needs a real console window. Run from Git Bash, CI or Claude Code, it crashes partway through, sometimes after the pak is already assembled, so a build can look failed when it worked. `mp_build_headless.py` runs `mp-build` with plain-text output instead. It passes its arguments to `mp-build` unchanged.

In a normal terminal window, plain `mp-build` from the `Management Pack` folder also works, as long as `config.json` has a registry.

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `Docker is not answering` | Docker Desktop is stopped or still starting. Its engine can also answer `500 Internal Server Error` for a while. | Start Docker Desktop, wait for **Engine running**, and check with `docker info`. |
| `mp-build did not finish in 15 minutes` | Usually `mp-build` waiting for an answer to a prompt | Check that `config.json` has `container_repository`. Read the end of `logs/build.log`. |
| `No pak for version … was built` | The build failed | Read the error at the end of `logs/build.log`. |
| The push fails with `denied` or `unauthorized` | Not logged in to the registry, or no write access | `docker login ghcr.io`, with an account that can write the package. |
| `base-adapter:python-1.0.0: not found` | An old `Dockerfile` that pulls the base image from VMware's registry, which no longer has it | Use the `Dockerfile` in this repo, which builds from the SDK's local base image. |
