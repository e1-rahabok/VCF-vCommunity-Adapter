# Screenshot Script

`screenshot.ps1` takes the documentation's screenshots of the VCF Operations UI, from the instance in `.secrets/vcf-ops.xml`, and saves them into `docs/`. Each screenshot is defined once in `screenshots.json`: the page, the clicks to get to what is shown, and the part of the window to keep. Running the script again updates them all, so the screenshots follow the UI and the pack's settings without being taken by hand.

## Safety

The script only looks. It opens pages and expands sections, and never clicks **Save**, **Delete** or anything else that changes the instance. A screenshot's steps must keep to that: see [Adding a screenshot](#adding-a-screenshot).

It logs in with the account in `.secrets/vcf-ops.xml`, the same way as [`install.ps1`](../install/install.md): an HTTP login to the UI, whose session is handed to the browser. Nothing is typed into the login page. The login is passed to Python in the process environment only, and is cleared when the script ends.

TLS certificates are not checked, as in the other tools. It is meant for a test instance on a trusted network.

## Requirements

- PowerShell 7 (`pwsh`).
- Python, with Playwright: `python -m pip install --user playwright`.
- Google Chrome. The script drives the installed Chrome in the background, so Playwright's own browser download is not needed.
- An account that can see the pages of the screenshots. The URL and login in `.secrets/vcf-ops.xml`, created as described in [Live Validation Test Plan](../validate/validate.md#requirements), or passed as parameters.

## Running it

From the repo root:

```powershell
# Update every screenshot
pwsh tools/screenshot/screenshot.ps1

# List the screenshots
pwsh tools/screenshot/screenshot.ps1 -List

# Update one, and keep a full-window screenshot after every step, to see what each step did
pwsh tools/screenshot/screenshot.ps1 -Name adapter-instance-advanced-settings -SaveSteps $env:TEMP\shots
```

| Parameter | Default | Meaning |
| :--- | :--- | :--- |
| `-Name` | all | Only these screenshots. |
| `-List` | off | List the screenshots and where each is saved, then stop. |
| `-SaveSteps` | off | A folder for a full-window screenshot after every step, and of the window when a step fails. |
| `-Url`, `-Credential`, `-SecretFile` | `.secrets/vcf-ops.xml` | Where to connect. |

Each screenshot prints its steps, then `saved <path>` or `FAILED` with the reason. Exit code `0` means every screenshot was saved, `1` that at least one failed. A failed screenshot leaves the file from the last run as it was.

## What it does

For each screenshot, in a new browser session:

1. Logs in over HTTP, as `install.ps1` does, and retries up to 3 times when the connection is reset.
2. Opens the page, at the window size of the screenshot.
3. Runs the steps in order. Each step waits up to 60 s for its element to be visible, then clicks it and waits for the UI to finish drawing.
4. Saves the capture into the repo.

Then it closes the session.

## Adding a screenshot

1. Show where it is and which part you want: a screenshot of the page with that part marked, or cropped.
2. Add an entry to `screenshots.json`.
3. Run it with `-Name` and `-SaveSteps`, and compare the result with the example. Adjust until they match.

After that, the screenshot is updated by every run, with no more examples needed.

An entry:

| Field | Meaning |
| :--- | :--- |
| `name` | Used with `-Name`. |
| `description` | What it shows. |
| `output` | Where it is saved, from the repo root. Images go in the `images/` folder of the guide that uses them (see [CONTRIBUTING](../../CONTRIBUTING.md#documentation)). |
| `page` | The page to open, from the instance's root, such as `/vcf-operations/ui/operate/administration/integrations;tab=accounts`. |
| `viewport` | The window size. Make it tall enough for everything captured to be on screen at once: a section that runs below the window is cut. Default 1600 × 1000. |
| `steps` | What to do, in order. See below. |
| `capture` | What to keep. See below. |

A step is one of:

| Step | Does |
| :--- | :--- |
| `{"click": "<selector>"}` | Clicks the first visible element that matches. `settle_ms` sets how long to wait afterwards (default 1,500 ms). |
| `{"wait_for": "<selector>"}` | Waits for an element to be visible. |
| `{"wait_ms": 2000}` | Waits a fixed time. |
| `{"goto": "<path>"}` | Opens another page. |

`frame` on a step or a capture looks in a frame of the page instead of the page itself. The older pages, such as Integrations → Accounts and the Adapter Instance settings, are in the frame `ops_iframe`.

The capture is one of:

| Capture | Keeps |
| :--- | :--- |
| `from`, `to` (and `width`, `padding`, `extend_left`) | The region from the top of `from` to the bottom of `to`, starting at the further left of the two, `width` pixels wide, with `padding` around it. |
| `element` | One element, as it is drawn. |
| nothing | The whole window. |

Selectors are [Playwright selectors](https://playwright.dev/python/docs/locators). Prefer what a person reads on the screen, such as `text="Advanced Settings"` (quoted: the exact text), over generated IDs such as `ext-element-48`, which change from one session to the next. A class such as `.chevron-medium-right` is fine when there is no text to click.

## Design decisions

**Playwright in the background, not a browser Claude controls.** Claude in Chrome, or the Claude desktop app's browser, can take a screenshot too, one click at a time, with a person logging in. A script needs no person, gives the same crop every time, and runs again for every update.

**The HTTP login, not the login page.** It is the login `install.ps1` already uses, so nothing types a password into a page, and a change to the login page does not break the screenshots.

**The installed Chrome.** Playwright can download its own browser, about 150 MB. The installed Chrome is enough, and draws the UI the way a person sees it.

**A region between two elements, not fixed pixels.** The section's first and last elements set the region, so it follows when a setting is added or the page moves.

## Troubleshooting

| Message | Cause | Fix |
| :--- | :--- | :--- |
| `Playwright is not installed` | Python has no Playwright | `python -m pip install --user playwright` |
| `UI login failed` | Wrong login in the secret file | Check `.secrets/vcf-ops.xml`. |
| `Timeout 60000ms exceeded` on a step | The element is not on the page: the UI changed, the item does not exist, or it is in a frame the step does not name | Run with `-SaveSteps` and look at the failed step's screenshot. |
| `frame 'ops_iframe' did not appear` | The page did not load the older UI | Check the `page` path. |
| A capture is cut at the bottom | The window is too short for the region | Raise the `viewport` height. |
| `Executable doesn't exist` for Chrome | Chrome is not installed | Install Google Chrome. |
