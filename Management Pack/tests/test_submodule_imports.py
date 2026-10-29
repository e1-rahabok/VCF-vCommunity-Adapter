#  Copyright 2026 VCF Operations vCommunity Management Pack
"""The app code imports the submodules it uses, by their full name.

"import concurrent" does not load concurrent.futures. The unit tests load it through the anyio pytest
plugin, so a bare import passes here and fails on the instance. See the Tests page, "Submodule imports".

Run from the "Management Pack" folder:  python -m pytest tests
"""
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
BARE_IMPORT = re.compile(r"^\s*import concurrent\s*$", re.MULTILINE)
USES_FUTURES = re.compile(r"\bconcurrent\.futures\.")
EXPLICIT_IMPORT = re.compile(r"^\s*import concurrent\.futures\s*$", re.MULTILINE)


def problems(text):
    found = []
    if BARE_IMPORT.search(text):
        found.append("import concurrent")
    if USES_FUTURES.search(text) and not EXPLICIT_IMPORT.search(text):
        found.append("concurrent.futures used without 'import concurrent.futures'")
    return found


def test_app_imports_concurrent_futures_by_full_name():
    failures = {}
    for path in APP.rglob("*.py"):
        found = problems(path.read_text(encoding="utf-8"))
        if found:
            failures[str(path.relative_to(APP.parent))] = found
    assert failures == {}


def test_check_flags_the_bare_import_that_failed_on_the_instance():
    old_line = "import xml.etree.ElementTree as ET\nimport concurrent\n\nwith concurrent.futures.ThreadPoolExecutor() as x:\n    pass\n"
    assert problems(old_line) == [
        "import concurrent",
        "concurrent.futures used without 'import concurrent.futures'",
    ]


def test_check_accepts_the_full_import():
    fixed = "import concurrent.futures\n\nwith concurrent.futures.ThreadPoolExecutor() as x:\n    pass\n"
    assert problems(fixed) == []
