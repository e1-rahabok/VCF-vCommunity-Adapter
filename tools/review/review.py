#!/usr/bin/env python3
"""Evidence checks for the engineering review pages. Read-only: it never changes a file in the repository.

It does three things, and reports what it finds. It does not judge the code.

  snapshot   Records the facts a review depends on: commit, pack version, tests collected,
             risky-pattern counts, docs link result. Optional linter runs.
  check      Reads the review pages in docs/development-guide/engineering-review and reports:
               citations  each file:line citation exists, and the line is in range
               trace      each finding ID has a decision, and each decision has evidence
               claims     the test counts and Python versions the pages state, for comparison

Usage, from the repository root:

    python tools/review/review.py snapshot [--out FILE] [--linters]
    python tools/review/review.py check [--rev REV] [--snapshot FILE] [--out FILE] [--fail]

Only the Python standard library is used. Nothing here is run by CI. See review.md.
"""
import argparse
import datetime
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Read-only means no cache either: the other checker scripts are loaded by path, and that would write __pycache__.
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = ROOT / "docs" / "development-guide" / "engineering-review"
PACK = ROOT / "Management Pack"
APP = PACK / "app"

ID_RE = re.compile(r"^[A-Z]{1,4}-\d{2}$")
REVIEW_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-(?:review|rescore)\.md$")
COMPLETED_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-completed\.md$")
DECISIONS = ("Implemented", "Partly", "Deferred", "Rejected", "No change")
REVISIT = ("Partly", "Deferred", "Rejected")
EVIDENCE = re.compile(r"#\d+|\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b|tests?/|test_\w+")
CITATION = re.compile(
    r"`((?:[\w.\- ]+/)*(?:[\w.\-]+\.(?:py|ps1|psm1|md|cfg|xml|json|txt|yml|yaml|csv|sh|toml|ini)|Dockerfile))"
    r"(?::(\d+)(?:-(\d+))?)?`"
)
PYTHON_CLAIM = re.compile(r"\bPython (\d+\.\d+(?:\.\d+)?)")
PASSED_CLAIM = re.compile(r"\b(\d+) passed\b")
CI_PYTHON = re.compile(r'python-version:\s*"?(\d+\.\d+(?:\.\d+)?)"?')

PATTERNS = {
    "while True (loop with no visible bound)": r"^\s*while True\b",
    "bare except": r"^\s*except\s*:",
    "shell=True": r"shell\s*=\s*True",
    "eval( or exec(": r"\b(?:eval|exec)\(",
    "pickle or yaml.load": r"\bpickle\b|yaml\.load\(",
    "certificate check off": r"verify\s*=\s*False|verify_ssl\s*=\s*False|SkipCertificateCheck|CERT_NONE",
    "noqa or nosec marker": r"#\s*(?:noqa|nosec)",
    "TODO or FIXME": r"\b(?:TODO|FIXME)\b",
    "print( call": r"^\s*print\(",
}


# ---------------------------------------------------------------- git and file access

def git(args, root=ROOT):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")


def tracked_files(rev=None, root=ROOT):
    """Repo-relative paths git tracks. With a revision, the paths at that commit."""
    if rev:
        out = git(["ls-tree", "-r", "--name-only", rev], root)
    else:
        out = git(["ls-files"], root)
    if out.returncode != 0:
        raise SystemExit(f"git failed: {out.stderr.strip()}")
    return [line for line in out.stdout.splitlines() if line]


def read_text(path, rev=None, root=ROOT):
    """File text now, or at a revision. Returns None when the file is not there."""
    if rev:
        out = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=root, capture_output=True, encoding="utf-8",
                             errors="replace")
        return out.stdout if out.returncode == 0 else None
    full = Path(root) / path
    if not full.is_file():
        return None
    return full.read_text(encoding="utf-8", errors="replace")


def snippet(text, number):
    lines = text.splitlines()
    if 1 <= number <= len(lines):
        return lines[number - 1].strip()[:90]
    return ""


# ---------------------------------------------------------------- citations

def resolve(path, files):
    """Find the repo file a citation names. Paths are tried from the repo root, the pack and its app folder."""
    tracked = set(files)
    for base in ("", "Management Pack/app", "Management Pack", "docs/development-guide/engineering-review"):
        candidate = os.path.normpath(os.path.join(base, path)).replace(os.sep, "/")
        if candidate in tracked:
            return candidate, "found"
    if "/" not in path:
        matches = [f for f in files if f == path or f.endswith("/" + path)]
        if len(matches) == 1:
            return matches[0], "found by name"
        if len(matches) > 1:
            return None, f"ambiguous: {len(matches)} files have this name"
    return None, "missing"


def check_citations(review_files, files, rev=None, root=ROOT):
    """review_files: repo-relative paths of review pages, read from the working tree.
    files: the paths the cited code is looked up in, at rev when one is given. Returns rows of
    (page, line, cited, status, detail)."""
    rows = []
    for page in review_files:
        text = read_text(page, None, root) or ""
        fenced = False
        for number, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                continue
            for m in CITATION.finditer(line):
                path, start, end = m.group(1).strip(), m.group(2), m.group(3)
                cited = path + (f":{start}" if start else "") + (f"-{end}" if end else "")
                found, how = resolve(path, files)
                if found is None:
                    rows.append((page, number, cited, "FAIL" if how == "missing" else "WARN", how))
                    continue
                if not start:
                    rows.append((page, number, cited, "PASS", how))
                    continue
                target = read_text(found, rev, root) or ""
                count = len(target.splitlines())
                last = int(end or start)
                if int(start) > count or last > count:
                    rows.append((page, number, cited, "FAIL", f"line out of range, file has {count} lines"))
                else:
                    rows.append((page, number, cited, "PASS", f"{how}; line reads: {snippet(target, int(start))}"))
    return rows


# ---------------------------------------------------------------- tables and trace

def table_rows(text):
    """Yield (line number, cells, header) for each table row outside code fences."""
    header, fenced = None, False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if not line.startswith("|"):
            header = None  # a table ends at the first line that is not a table row
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
            continue
        if cells and cells[0] == "ID":
            header = cells
            continue
        yield number, cells, header


def finding_ids(text):
    """Finding IDs in the first column of any table row."""
    ids = {}
    for number, cells, _ in table_rows(text):
        if cells and ID_RE.match(cells[0]):
            ids.setdefault(cells[0], number)
    return ids


def decisions(text):
    """Decision rows of a response page: id -> (decision, action, line). Rows need a Decision column."""
    out = {}
    for number, cells, header in table_rows(text):
        if not header or "Decision" not in header or not cells or not ID_RE.match(cells[0]):
            continue
        value = cells[header.index("Decision")] if len(cells) > header.index("Decision") else ""
        action = cells[header.index("Action taken")] if "Action taken" in header and len(cells) > header.index(
            "Action taken") else ""
        if cells[0] in out:
            # A second row for the same ID: keep the first, and mark it as a duplicate.
            first = out[cells[0]]
            out[cells[0]] = (first[0], first[1], first[2], True)
        else:
            out[cells[0]] = (value, action, number, False)
    return out


def mentions(text, finding):
    return re.search(rf"\b{re.escape(finding)}\b", text) is not None


def check_trace(review_dir=REVIEW_DIR, root=ROOT):
    """Compare each review page with its response page (same date) and later re-reviews.
    Returns rows of (status, page, line, message)."""
    rows = []
    reviews, responses = {}, {}
    for path in sorted(Path(review_dir).glob("*.md")):
        m_review = REVIEW_NAME.match(path.name)
        m_done = COMPLETED_NAME.match(path.name)
        if m_review:
            reviews[m_review.group(1)] = path
        elif m_done:
            responses[m_done.group(1)] = path
    texts = {d: p.read_text(encoding="utf-8") for d, p in reviews.items()}
    for d, p in responses.items():
        texts[d + "_response"] = p.read_text(encoding="utf-8")
    rel = lambda p: os.path.relpath(p, root).replace(os.sep, "/")
    ids_by_date = {d: finding_ids(texts[d]) for d in reviews}
    all_ids = set().union(*ids_by_date.values()) if ids_by_date else set()

    for date in sorted(set(reviews) | set(responses)):
        if date in reviews and date not in responses:
            new = [i for i in ids_by_date[date] if not any(i in ids_by_date[d] for d in reviews if d < date)]
            rows.append(("INFO", rel(reviews[date]), 0,
                         f"no response page yet; {len(ids_by_date[date])} IDs, {len(new)} not in an earlier review"))
            continue
        if date not in reviews:
            rows.append(("WARN", rel(responses[date]), 0, "response page has no review page with the same date"))
            continue
        # Dates with a response page are checked below, against the review of the same date.
        ids = ids_by_date[date]
        done = decisions(texts[date + "_response"])
        for finding, line in ids.items():
            if finding not in done:
                rows.append(("FAIL", rel(reviews[date]), line, f"{finding} has no decision in the response page"))
        for finding, (value, action, line, dup) in done.items():
            where = rel(responses[date])
            if dup:
                rows.append(("FAIL", where, line, f"{finding} has more than one decision row"))
            if finding not in all_ids:
                rows.append(("WARN", where, line, f"{finding} is not in any review page"))
            if value not in DECISIONS:
                rows.append(("FAIL", where, line, f"{finding}: decision '{value}' is not one of {', '.join(DECISIONS)}"))
                continue
            if value == "Implemented" and not EVIDENCE.search(action):
                rows.append(("WARN", where, line, f"{finding} is Implemented, but the action names no issue, commit or test"))
            if value in REVISIT:
                later = [d for d in reviews if d > date]
                if later and not any(mentions(texts[d], finding) for d in later):
                    rows.append(("WARN", where, line, f"{finding} ({value}) is not mentioned in any later review"))
    return rows


# ---------------------------------------------------------------- claims

def check_claims(review_dir=REVIEW_DIR, snapshot=None):
    """Lists the Python versions and pass counts the pages state. Shown beside the snapshot, not judged."""
    rows = []
    for path in sorted(Path(review_dir).glob("*.md")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for m in PYTHON_CLAIM.finditer(line):
                rows.append((path.name, number, f"Python {m.group(1)}", "compare with the snapshot's CI Python and tool Python"))
            for m in PASSED_CLAIM.finditer(line):
                if snapshot and snapshot.get("tests_collected") is not None:
                    note = f"snapshot collected {snapshot['tests_collected']} tests"
                else:
                    note = "no test count in the snapshot"
                rows.append((path.name, number, f"{m.group(1)} passed", note))
    return rows


# ---------------------------------------------------------------- snapshot

def count_patterns(app):
    counts = {name: 0 for name in PATTERNS}
    py_files, py_lines = 0, 0
    compiled = {name: re.compile(p) for name, p in PATTERNS.items()}
    for path in sorted(Path(app).rglob("*.py")):
        py_files += 1
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            py_lines += 1
            for name, rx in compiled.items():
                if rx.search(line):
                    counts[name] += 1
    return py_files, py_lines, counts


def collect_tests():
    """Number of unit tests pytest collects, with a note. Collects only: no test runs, no bytecode is written."""
    if importlib.util.find_spec("pytest") is None:
        return None, "pytest is not installed for this Python"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "tests"],
                         cwd=PACK, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                         timeout=600)
    text = out.stdout + out.stderr
    m = re.search(r"(\d+) tests? collected", text)
    if m and out.returncode == 0:
        return int(m.group(1)), "collected"
    # Collection errors (for example a missing SDK) stop pytest before it reports a count.
    last = [l for l in text.splitlines() if l.strip()][-1:] or ["no output"]
    return (int(m.group(1)) if m else None), f"collection did not finish cleanly: {last[0][:120]}"


def run_linter(name, argv):
    if name == "ruff" and importlib.util.find_spec("ruff") is None:
        return {"status": "not installed"}
    if name == "bandit" and importlib.util.find_spec("bandit") is None:
        return {"status": "not installed"}
    if name == "pip-audit" and importlib.util.find_spec("pip_audit") is None:
        return {"status": "not installed"}
    out = subprocess.run([sys.executable, "-m", *argv], cwd=PACK, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=900)
    tail = [l for l in (out.stdout + out.stderr).splitlines() if l.strip()][-3:]
    return {"status": "passed" if out.returncode == 0 else f"exit {out.returncode}", "tail": tail}


def load_checker(name, folder):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / folder / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(linters=False):
    manifest = json.loads((PACK / "manifest.txt").read_text(encoding="utf-8"))
    head = git(["rev-parse", "--short", "HEAD"]).stdout.strip()
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    dirty = bool(git(["status", "--porcelain"]).stdout.strip())
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    ci_python = CI_PYTHON.search(ci)
    py_files, py_lines, counts = count_patterns(APP)
    docs_pages = len([f for f in tracked_files() if f.startswith("docs/") and f.endswith(".md")])
    links = load_checker("check_links", "check-docs").check(str(ROOT))
    tests, tests_note = collect_tests()
    data = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": head,
        "branch": branch,
        "uncommitted_changes": dirty,
        "pack_version": manifest.get("version"),
        "tool_python": sys.version.split()[0],
        "ci_python": ci_python.group(1) if ci_python else None,
        "tests_collected": tests,
        "tests_collected_note": tests_note,
        "app_python_files": py_files,
        "app_python_lines": py_lines,
        "pattern_counts": counts,
        "docs_pages": docs_pages,
        "broken_links": len(links),
    }
    if linters:
        data["linters"] = {
            "ruff": run_linter("ruff", ["ruff", "check", "app", "tests"]),
            "bandit": run_linter("bandit", ["bandit", "-r", "app", "-q"]),
            "pip-audit": run_linter("pip-audit", ["pip_audit", "-r", "adapter_requirements.txt"]),
        }
    return data


# ---------------------------------------------------------------- report

def markdown(snap, citations, trace, claims, rev):
    out = ["# Engineering review evidence check", ""]
    out.append(f"- Citations checked against: {rev or 'the working tree'}")
    if snap:
        out.append(f"- Snapshot: commit `{snap['commit']}`, pack `{snap['pack_version']}`, "
                   f"generated {snap['generated_at']}, uncommitted changes: {snap['uncommitted_changes']}")
    out.append("")
    fails = sum(1 for c in citations if c[3] == "FAIL") + sum(1 for t in trace if t[0] == "FAIL")
    warns = sum(1 for c in citations if c[3] == "WARN") + sum(1 for t in trace if t[0] == "WARN")
    out.append(f"**Summary:** {fails} FAIL, {warns} WARN. "
               "A FAIL is a broken citation or a missing decision. A WARN needs a look. "
               "The tool does not judge the code.")
    out.append("")
    out.append("## 1. Citations")
    out.append("")
    out.append("| Page | Line | Cited | Result | Detail |")
    out.append("| :--- | ---: | :--- | :--- | :--- |")
    for page, number, cited, status, detail in citations:
        out.append(f"| {os.path.basename(page)} | {number} | `{cited}` | {status} | {detail} |")
    if not citations:
        out.append("| | | none found | | |")
    out.append("")
    out.append("## 2. Findings, decisions and re-reviews")
    out.append("")
    for status, page, line, message in trace:
        where = f"{page}:{line}" if line else page
        out.append(f"- **{status}** `{where}`: {message}")
    if not trace:
        out.append("- No issues found.")
    out.append("")
    out.append("## 3. Stated claims, for comparison")
    out.append("")
    out.append("| Page | Line | Claim | Note |")
    out.append("| :--- | ---: | :--- | :--- |")
    for page, number, claim, note in claims:
        out.append(f"| {page} | {number} | {claim} | {note} |")
    if not claims:
        out.append("| | | none found | |")
    out.append("")
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("snapshot", help="record the facts a review depends on")
    s.add_argument("--out", help="write JSON here instead of printing it")
    s.add_argument("--linters", action="store_true", help="also run ruff, bandit and pip-audit (slow)")
    c = sub.add_parser("check", help="report citations, decisions and stated claims")
    c.add_argument("--rev", help="check citations against this commit (default: the working tree)")
    c.add_argument("--snapshot", help="a JSON file from the snapshot command")
    c.add_argument("--out", help="write the Markdown report here instead of printing it")
    c.add_argument("--fail", action="store_true", help="exit 1 when the report has a FAIL (for people, not CI)")
    args = parser.parse_args(argv)

    if args.command == "snapshot":
        text = json.dumps(snapshot(args.linters), indent=2)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0

    snap = json.loads(Path(args.snapshot).read_text(encoding="utf-8")) if args.snapshot else None
    # The review pages are always read from the working tree. Only the code they cite can come from --rev.
    review_pages = sorted(
        f for f in tracked_files()
        if f.startswith("docs/development-guide/engineering-review/") and REVIEW_NAME.match(os.path.basename(f))
    )
    citations = check_citations(review_pages, tracked_files(args.rev), args.rev)
    trace = check_trace()
    claims = check_claims(snapshot=snap)
    report = markdown(snap, citations, trace, claims, args.rev)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    else:
        print(report)
    failed = any(c[3] == "FAIL" for c in citations) or any(t[0] == "FAIL" for t in trace)
    return 1 if args.fail and failed else 0


if __name__ == "__main__":
    sys.exit(main())
