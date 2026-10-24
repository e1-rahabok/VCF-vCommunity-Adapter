"""Take the screenshots defined in screenshots.json from a VCF Operations instance.

Run through screenshot.ps1, which reads the login from .secrets/vcf-ops.xml and passes it in the
environment (OPS_URL, OPS_USER, OPS_PASSWORD). Nothing is typed into the login page: the session comes
from the same HTTP login as tools/install/install.ps1, and its cookies are handed to the browser.

Each shot opens a page, follows its steps (clicks to expand or open something), and saves a capture.
Shots only look: a step must never save, delete or change anything on the instance.

Usage: python screenshot.py [--name NAME ...] [--list] [--save-steps DIR]
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFINITIONS = HERE / "screenshots.json"
DEFAULT_VIEWPORT = {"width": 1600, "height": 1000}
STEP_TIMEOUT_MS = 60_000
SETTLE_MS = 1_500           # after each click, for the UI to finish drawing
LOGIN_ATTEMPTS = 3          # the lab sometimes resets a connection


def login(context, root: str) -> None:
    """Log in over HTTP, as install.ps1 does. The cookies land in the browser context."""
    form = {
        "mainAction": "login", "userName": os.environ["OPS_USER"], "password": os.environ["OPS_PASSWORD"],
        "authSourceId": "localItem", "authSourceName": "Local Account", "authSourceType": "",
        "forceLogin": "false", "timezone": "0", "languageCode": "us",
    }
    for attempt in range(1, LOGIN_ATTEMPTS + 1):
        try:
            context.request.get(f"{root}/ui/login.action?vcf=1")
            answer = context.request.post(f"{root}/ui/login.action", form=form).text().strip()
            if answer != "ok":
                raise RuntimeError(f"UI login failed: {answer[:200]}")
            # Sets OPS_SESSION. Following its redirect would make the session invalid.
            context.request.get(f"{root}/ui/index.action", max_redirects=0)
            return
        except PlaywrightError as e:
            if attempt == LOGIN_ATTEMPTS:
                raise
            print(f"  login attempt {attempt} failed ({str(e).splitlines()[0]}), retrying")
            time.sleep(5)


def scope(page, frame_name):
    """The page itself, or the named frame inside it (the older pages run in the frame ops_iframe)."""
    if not frame_name:
        return page
    end = time.time() + STEP_TIMEOUT_MS / 1000
    while time.time() < end:
        frame = page.frame(name=frame_name)
        if frame:
            return frame
        page.wait_for_timeout(500)
    raise RuntimeError(f"frame '{frame_name}' did not appear")


def visible(where, selector: str):
    locator = where.locator(selector).locator("visible=true").first
    locator.wait_for(state="visible", timeout=STEP_TIMEOUT_MS)
    return locator


def run_step(page, root: str, step: dict) -> str:
    where = scope(page, step.get("frame"))
    if "goto" in step:
        page.goto(root + step["goto"], wait_until="domcontentloaded")
        return f"goto {step['goto']}"
    if "click" in step:
        visible(where, step["click"]).click()
        page.wait_for_timeout(step.get("settle_ms", SETTLE_MS))
        return f"click {step['click']}"
    if "wait_for" in step:
        visible(where, step["wait_for"])
        return f"wait_for {step['wait_for']}"
    if "wait_ms" in step:
        page.wait_for_timeout(step["wait_ms"])
        return f"wait {step['wait_ms']} ms"
    raise ValueError(f"unknown step: {step}")


def capture(page, shot: dict, out: Path) -> None:
    """Save the capture: a region between two elements, one element, or the whole window."""
    spec = shot.get("capture", {})
    where = scope(page, spec.get("frame"))
    pad = spec.get("padding", 0)
    if "from" in spec:
        top = visible(where, spec["from"]).bounding_box()
        bottom = visible(where, spec.get("to", spec["from"])).bounding_box()
        left = min(top["x"], bottom["x"])          # the further left of the two, so neither is cut
        x = max(left - pad - spec.get("extend_left", 0), 0)
        y = max(top["y"] - pad, 0)
        width = spec.get("width", top["width"]) + 2 * pad + spec.get("extend_left", 0)
        height = bottom["y"] + bottom["height"] - top["y"] + 2 * pad
        page.screenshot(path=str(out), clip={"x": x, "y": y, "width": width, "height": height})
    elif "element" in spec:
        visible(where, spec["element"]).screenshot(path=str(out))
    else:
        page.screenshot(path=str(out))


def run_shot(browser, root: str, shot: dict, save_steps: Path = None) -> Path:
    context = browser.new_context(ignore_https_errors=True, viewport=shot.get("viewport", DEFAULT_VIEWPORT))
    try:
        login(context, root)
        page = context.new_page()
        page.goto(root + shot["page"], wait_until="domcontentloaded")
        for number, step in enumerate(shot.get("steps", []), start=1):
            try:
                print(f"  step {number}: {run_step(page, root, step)}")
            except Exception:
                if save_steps:
                    page.screenshot(path=str(save_steps / f"{shot['name']}-failed-step{number}.png"))
                raise
            if save_steps:
                page.screenshot(path=str(save_steps / f"{shot['name']}-step{number}.png"))
        out = REPO / shot["output"]
        out.parent.mkdir(parents=True, exist_ok=True)
        capture(page, shot, out)
        return out
    finally:
        context.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", action="append", help="only this shot (repeatable)")
    parser.add_argument("--list", action="store_true", help="list the shots and exit")
    parser.add_argument("--save-steps", type=Path, help="also save a full-window screenshot after every step here")
    args = parser.parse_args()

    shots = json.loads(DEFINITIONS.read_text(encoding="utf-8"))["shots"]
    if args.list:
        for shot in shots:
            print(f"{shot['name']:<40} {shot['output']}  {shot.get('description', '')}")
        return 0
    if args.name:
        unknown = set(args.name) - {shot["name"] for shot in shots}
        if unknown:
            print(f"Unknown shot(s): {', '.join(sorted(unknown))}. Use --list.")
            return 1
        shots = [shot for shot in shots if shot["name"] in args.name]
    if args.save_steps:
        args.save_steps.mkdir(parents=True, exist_ok=True)

    root = os.environ["OPS_URL"].rstrip("/")
    failed = 0
    with sync_playwright() as p:
        # The installed Chrome: no separate browser download is needed.
        browser = p.chromium.launch(channel="chrome", headless=True)
        try:
            for shot in shots:
                print(f"[{shot['name']}]")
                try:
                    out = run_shot(browser, root, shot, args.save_steps)
                    print(f"  saved {out.relative_to(REPO)} ({out.stat().st_size // 1024} KB)")
                except Exception as e:
                    failed += 1
                    print(f"  FAILED: {type(e).__name__}: {str(e).splitlines()[0][:300]}")
        finally:
            browser.close()
    print(f"RESULT: {'FAILED' if failed else 'PASSED'}  {len(shots) - failed} of {len(shots)} saved")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
