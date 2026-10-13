"""Check every relative link and image in the repository's Markdown files.

Fails on a link to a file that does not exist, or to a heading anchor that
the target page does not have. Web links are not checked.

Usage, from the repository root:

    python tools/check-docs/check_links.py
"""
import os
import re
import subprocess
import sys
from urllib.parse import unquote

LINK = re.compile(r"\]\(([^)\s]+)\)")
HEADING = re.compile(r"^(?:>\s*)*#{1,6}\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


def repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", ".."))


def markdown_files(root):
    out = subprocess.check_output(["git", "-c", "core.quotePath=false", "ls-files", "*.md"], cwd=root, text=True)
    return [line for line in out.splitlines() if line]


def slug(heading):
    """GitHub's anchor for a heading."""
    text = re.sub(r"`|\*\*|__", "", heading).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(path):
    found, seen, fenced = set(), {}, False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if FENCE.match(line):
                fenced = not fenced
                continue
            m = None if fenced else HEADING.match(line)
            if m:
                base = slug(m.group(1))
                n = seen.get(base, 0)
                seen[base] = n + 1
                found.add(base if n == 0 else f"{base}-{n}")
    return found


def links(path):
    fenced = False
    with open(path, encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            if FENCE.match(line):
                fenced = not fenced
                continue
            if not fenced:
                for m in LINK.finditer(line):
                    yield number, m.group(1)


def check(root):
    errors = []
    cache = {}
    for md in markdown_files(root):
        for number, target in links(os.path.join(root, md)):
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            path, _, fragment = target.partition("#")
            dest = os.path.normpath(os.path.join(os.path.dirname(md), unquote(path))) if path else md
            full = os.path.join(root, dest)
            if not os.path.exists(full):
                errors.append(f"{md}:{number}: missing file: {target}")
                continue
            if fragment and dest.endswith(".md"):
                if dest not in cache:
                    cache[dest] = anchors(full)
                if fragment.lower() not in cache[dest]:
                    errors.append(f"{md}:{number}: missing anchor: {target}")
    return errors


def main():
    errors = check(repo_root())
    for e in errors:
        print(e)
    print(f"{len(errors)} broken link(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
