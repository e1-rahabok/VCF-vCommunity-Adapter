"""Take the screenshots defined in screenshots.json from a VCF Operations instance.

Run through screenshot.ps1, which reads the login from .secrets/vcf-ops.xml and passes it in the
environment (OPS_URL, OPS_USER, OPS_PASSWORD). Nothing is typed into the login page: the session comes
from the same HTTP login as tools/install/install.ps1, and its cookies are handed to the browser.

Each shot opens a page, follows its steps (clicks to expand or open something), and saves a capture.
Shots only look: a step must never save, delete or change anything on the instance.

Usage: python screenshot.py [--name NAME ...] [--list] [--save-steps DIR]
       python screenshot.py --inspect TEXT (--page PATH | --name NAME)
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
    if "hide" in step:
        # Hidden in this browser only, such as a banner the screenshot should not show. Nothing is sent.
        # Waits a little for it to be drawn; when it never appears, there is nothing to hide.
        try:
            where.locator(step["hide"]).first.wait_for(state="attached", timeout=step.get("timeout_ms", 10_000))
        except PlaywrightError:
            pass
        count = where.locator(step["hide"]).evaluate_all("els => els.map(e => e.style.setProperty('display', 'none', 'important')).length")
        return f"hide {step['hide']} ({count} element(s))"
    if "wait_ms" in step:
        page.wait_for_timeout(step["wait_ms"])
        return f"wait {step['wait_ms']} ms"
    raise ValueError(f"unknown step: {step}")


def capture(page, shot: dict, out: Path) -> None:
    """Save the capture: a region between two elements, one element, or the whole window."""
    spec = shot.get("capture", {})
    where = scope(page, spec.get("frame"))
    pad = spec.get("padding", 0)
    page.mouse.move(0, 0)               # no hover highlight or tooltip in the capture
    page.wait_for_timeout(500)
    if "from" in spec:
        top = visible(where, spec["from"]).bounding_box()
        # "to" can list several elements: the region ends at the lowest of them.
        ends = spec.get("to", spec["from"])
        boxes = [visible(where, s).bounding_box() for s in (ends if isinstance(ends, list) else [ends])]
        bottom = max(boxes, key=lambda b: b["y"] + b["height"])
        left = min([top["x"]] + [b["x"] for b in boxes])   # the furthest left, so nothing is cut
        x = max(left - pad - spec.get("extend_left", 0), 0)
        y = max(top["y"] - pad, 0)
        width = spec.get("width", top["width"]) + 2 * pad + spec.get("extend_left", 0)
        height = bottom["y"] + bottom["height"] - top["y"] + 2 * pad
        page.screenshot(path=str(out), clip={"x": x, "y": y, "width": width, "height": height})
    elif "element" in spec:
        visible(where, spec["element"]).screenshot(path=str(out))
    else:
        page.screenshot(path=str(out))


def open_shot_page(context, root: str, shot: dict, save_steps: Path = None):
    """Log in, open the shot's page and run its steps. Returns the page, ready to capture or inspect."""
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
    return page


def run_shot(browser, root: str, shot: dict, save_steps: Path = None) -> Path:
    context = browser.new_context(ignore_https_errors=True, viewport=shot.get("viewport", DEFAULT_VIEWPORT))
    try:
        page = open_shot_page(context, root, shot, save_steps)
        out = REPO / shot["output"]
        out.parent.mkdir(parents=True, exist_ok=True)
        capture(page, shot, out)
        return out
    finally:
        context.close()


# Messages of a dropped or refused connection. A shot that fails with one of these is tried once more; a
# shot that fails for another reason, such as an element that is not there, would fail again.
NETWORK_ERRORS = ("ECONNRESET", "ECONNREFUSED", "ECONNABORTED", "ETIMEDOUT", "EPIPE", "socket hang up", "net::ERR_")
RETRY_WAIT_S = 10


def is_network_error(error: Exception) -> bool:
    return any(marker in str(error) for marker in NETWORK_ERRORS)


# --- Inspect --------------------------------------------------------------------------------------------------
# What a new shot needs to know about an element: where it is, how it is built, and what to click.
DESCRIBE = """e => {
  const cls = n => (n.className && n.className.baseVal === undefined ? n.className : '').toString().trim().replace(/\\s+/g, '.');
  const tag = n => n.tagName.toLowerCase() + (cls(n) ? '.' + cls(n).slice(0, 80) : '');
  const ancestors = [];
  for (let n = e.parentElement; n && ancestors.length < 6; n = n.parentElement) ancestors.push(tag(n));
  const isExpander = x => /expander|chevron|caret|toggle|collapse/i.test(cls(x));
  // The row that holds it; without one, the nearest container (up to 8 levels) that has an expander.
  let row = e.closest('tr, [role=row], .x-grid-item, clr-dg-row, li');
  for (let n = e.parentElement, i = 0; !row && n && i < 8; n = n.parentElement, i++)
    if (Array.from(n.querySelectorAll('*')).some(isExpander)) row = n;
  const clickable = row ? Array.from(row.querySelectorAll('*')).filter(isExpander).map(tag).slice(0, 4) : [];
  const box = e.getBoundingClientRect();
  const style = getComputedStyle(e);
  return {
    visible: box.width > 0 && box.height > 0 && box.bottom > 0 && style.visibility !== 'hidden',
    element: tag(e), text: e.textContent, ancestors,
    row: row ? tag(row) + ' (expanded: ' + /tree-node-expanded|expanded/.test(cls(row)) + ')' : null,
    rowText: row ? row.innerText.replace(/\\s+/g, ' ').trim().slice(0, 80) : null,
    clickable, box: [Math.round(box.x), Math.round(box.y), Math.round(box.width), Math.round(box.height)],
  };
}"""


def inspect(page, text: str, timeout_s: int = 60) -> int:
    """Print what a shot needs to know about every element that shows text, in every frame of the page."""
    end = time.time() + timeout_s
    while time.time() < end and not any(f.get_by_text(text).count() for f in page.frames):
        page.wait_for_timeout(1000)
    # Elements that show exactly the text come first; elements that only contain it, when there are none.
    exact = any(f.get_by_text(text, exact=True).count() for f in page.frames)
    print(f"Showing {'exact' if exact else 'partial'} matches.")
    found = 0
    for frame in page.frames:
        # All matches described in one call: the older pages redraw parts of a tree, so an element counted
        # first can be gone a moment later.
        descriptions = frame.get_by_text(text, exact=exact).evaluate_all(f"els => els.slice(0, 8).map({DESCRIBE})")
        for d in descriptions:
            found += 1
            raw = d["text"]
            exact_ok = raw.strip() == text and " " not in raw
            frame_name = frame.name or "(the page itself)"
            print(f"\nMatch {found}: frame {frame_name!r}, visible {d['visible']}, at x,y,w,h {d['box']}")
            print(f"  element:   {d['element']}")
            print(f"  text:      {raw!r}" + ("" if exact_ok else "  <- not an exact match: use text=..., unquoted"))
            print(f"  ancestors: {' < '.join(d['ancestors'])}")
            if d["row"]:
                print(f"  row:       {d['row']}: {d['rowText']!r}")
            if d["clickable"]:
                print(f"  expanders in the row: {', '.join(d['clickable'])}")
            # Printed as JSON, ready to paste into screenshots.json.
            step = {"frame": frame.name} if frame.name else {}
            print(f"  suggested: {json.dumps({**step, 'click': f'text={json.dumps(text)}' if exact_ok else f'text={text}'})}")
            row = d["row"] or ""
            if "x-grid-row" in row and any("x-tree-expander" in c for c in d["clickable"]):
                has = f":has(:text-is('{text}'))" if exact_ok else f":has-text('{text}')"
                expand = f"tr.x-grid-row:not(.x-grid-tree-node-expanded){has} .x-tree-expander"
                print(f"  to expand: {json.dumps({**step, 'click': expand})}")
    if not found:
        print(f"\n'{text}' was not found in any frame within {timeout_s} s.")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", action="append", help="only this shot (repeatable)")
    parser.add_argument("--list", action="store_true", help="list the shots and exit")
    parser.add_argument("--save-steps", type=Path, help="also save a full-window screenshot after every step here")
    parser.add_argument("--inspect", help="describe the elements that show this text, instead of taking screenshots")
    parser.add_argument("--page", help="with --inspect: the page to open, from the instance's root")
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
    with sync_playwright() as p:
        # The installed Chrome: no separate browser download is needed.
        browser = p.chromium.launch(channel="chrome", headless=True)
        try:
            if args.inspect:
                return run_inspect(browser, root, args, shots)
            return run_shots(browser, root, shots, args.save_steps)
        finally:
            browser.close()


def run_inspect(browser, root: str, args, shots) -> int:
    """--inspect: on --page as it opens, or on a shot's page after its steps (--name, one shot)."""
    if args.page:
        shot = {"name": "inspect", "page": args.page}
    elif args.name and len(shots) == 1:
        shot = shots[0]
    else:
        print("--inspect needs --page, or --name with one shot.")
        return 1
    context = browser.new_context(ignore_https_errors=True, viewport=shot.get("viewport", DEFAULT_VIEWPORT))
    try:
        print(f"[inspect '{args.inspect}' on {shot['page']}" + (f" after the steps of {shot['name']}]" if not args.page else "]"))
        try:
            page = open_shot_page(context, root, shot, args.save_steps)
        except Exception as e:
            print(f"  FAILED before inspecting: {type(e).__name__}: {str(e).splitlines()[0][:300]}")
            return 1
        found = inspect(page, args.inspect)
        if args.save_steps:
            page.screenshot(path=str(args.save_steps / "inspect.png"))
        return 0 if found else 1
    finally:
        context.close()


def run_shots(browser, root: str, shots, save_steps: Path) -> int:
    failed = 0
    for shot in shots:
        print(f"[{shot['name']}]")
        for attempt in (1, 2):
            try:
                out = run_shot(browser, root, shot, save_steps)
                print(f"  saved {out.relative_to(REPO)} ({out.stat().st_size // 1024} KB)")
                break
            except Exception as e:
                message = f"{type(e).__name__}: {str(e).splitlines()[0][:300]}"
                if attempt == 1 and is_network_error(e):
                    print(f"  network error ({message}), trying the shot once more in {RETRY_WAIT_S} s")
                    time.sleep(RETRY_WAIT_S)
                    continue
                failed += 1
                print(f"  FAILED: {message}")
                break
    print(f"RESULT: {'FAILED' if failed else 'PASSED'}  {len(shots) - failed} of {len(shots)} saved")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
