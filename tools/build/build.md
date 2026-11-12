# Build Script

`build.ps1` builds the management pack's `.pak` file without prompts. It runs `mp-build` from the [VCF Operations Integration SDK](https://github.com/vmware/vmware-aria-operations-integration-sdk) in a way that works from a script, from CI, or from an AI coding assistant, none of which has a Windows console.

To install the result on the test instance, see [Install Script](../install/install.md).

## What it produces

| Output | Where |
| :--- | :--- |
| The `.pak` file, `vCommunity_<version>.pak` | `Management Pack/build/` (gitignored) |
| The adapter's container image | Pushed to `ghcr.io/e1-rahabok/vcf-operations-vcommunity`, tagged `<version>_<timestamp>` |

The pak does not contain the adapter's code. It names the image to run, and each Cloud Proxy pulls that image from the registry. So every build pushes an image, and a pak works only while its image is in the registry. See [How It Works](../../docs/installation-guide/how-it-works.md).

The version comes from `Management Pack/manifest.txt`.

## Requirements

- PowerShell 7 (`pwsh`).
- Python 3.9 to 3.12, with the Integration SDK 1.3 or later. `pip install -r "Management Pack/requirements.txt"` installs the pinned version. SDK 1.3 does not support Python 3.13: there the requirements file fails to install, and an unpinned `pip install vmware-aria-operations-integration-sdk` picks an old release whose `mp-build` cannot build this pack.
- Docker Desktop, running. The SDK builds the image locally from its own base image, `base-adapter:python-1.2.0` (see `Management Pack/Dockerfile`).
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

The script ends with the path and size of the pak, such as `Built …\Management Pack\build\vCommunity_<version>.pak (424 KB)`, and exits `0`. It exits `1` when no pak for the manifest version was made.

## What it does

1. **Checks Docker.** It stops at once if the Docker engine does not answer, so `mp-build` does not fail halfway through.
2. **Sets the registry.** `mp-build` reads the registry from `Management Pack/config.json`, and prompts for one when it is empty. That file is gitignored, so a fresh clone has none. The script writes `-Registry` into it.
3. **Runs `mp-build`** through `mp_build_headless.py`, with no keyboard input. `mp-build` then:
   1. builds the adapter image,
   2. starts it, and checks that the adapter answers and that its `describe.xml` is valid,
   3. tags the image and pushes it,
   4. assembles the pak.
4. **Checks for the pak.** It looks for a pak for the manifest version written during this run. It does not trust `mp-build`'s exit code, which is unreliable.

`mp-build` logs every step in `Management Pack/logs/build.log`. Look there first when a build fails.

## Why a wrapper

`mp-build` prints its progress with `prompt_toolkit`, which on Windows needs a real console window. Run from Git Bash, CI or an assistant, it crashes partway through, sometimes after the pak is already assembled, so a build that worked can look failed. `mp_build_headless.py` runs `mp-build` with plain-text output instead, and passes its arguments through unchanged.

In a normal terminal window, plain `mp-build` from the `Management Pack` folder also works, as long as `config.json` has a registry.

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `Docker is not answering` | Docker Desktop is stopped or still starting. Its engine can also answer `500 Internal Server Error` for a while. | Start Docker Desktop, wait for **Engine running**, and check with `docker info`. |
| `mp-build did not finish in 15 minutes` | Usually `mp-build` waiting for an answer to a prompt | Check that `config.json` has `container_repository`, and read the end of `logs/build.log`. |
| `No pak for version … was built` | The build failed | Read the error at the end of `logs/build.log`. |
| The push fails with `denied` or `unauthorized` | Not logged in to the registry, or no write access | Run `docker login ghcr.io` with an account that can write the package. |
| `base-adapter:python-1.0.0: not found` | An old `Dockerfile` that pulls the base image from VMware's registry, which no longer has it | Use the `Dockerfile` in this repo, which builds from the SDK's local base image. |
