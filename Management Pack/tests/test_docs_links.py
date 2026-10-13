#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Every relative link and image in the repository's Markdown files resolves.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import importlib.util
from pathlib import Path

CHECKER = Path(__file__).resolve().parents[2] / "tools" / "check-docs" / "check_links.py"


def test_no_broken_links():
    spec = importlib.util.spec_from_file_location("check_links", CHECKER)
    check_links = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check_links)
    assert check_links.check(check_links.repo_root()) == []
