#  Copyright 2026 VCF Operations vCommunity Management Pack
"""The engineering review evidence tool finds broken citations, missing decisions and weak evidence.

Each test builds a small fake repository in a temporary folder. Nothing here reads the real review pages.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import importlib.util
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[2] / "tools" / "review" / "review.py"

spec = importlib.util.spec_from_file_location("review", TOOL)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)

REVIEW_DIR = "docs/development-guide/engineering-review"
CODE = "line one\ndef publish():\n    return 1\n"


@pytest.fixture
def repo(tmp_path):
    """A fake repository: one code file under the app folder, and an empty review folder."""
    (tmp_path / "Management Pack" / "app" / "utils").mkdir(parents=True)
    (tmp_path / "Management Pack" / "app" / "utils" / "tls.py").write_text(CODE, encoding="utf-8")
    (tmp_path / REVIEW_DIR).mkdir(parents=True)
    return tmp_path


def write_page(repo, name, text):
    path = repo / REVIEW_DIR / name
    path.write_text(text, encoding="utf-8")
    return path


def files_of(repo):
    return [str(p.relative_to(repo)).replace("\\", "/") for p in repo.rglob("*") if p.is_file()]


# ---------------------------------------------------------------- citations

def test_resolve_tries_the_pack_app_folder(repo):
    found, how = review.resolve("utils/tls.py", files_of(repo))
    assert found == "Management Pack/app/utils/tls.py"
    assert how == "found"


def test_resolve_finds_a_bare_name_only_when_it_is_unique(repo):
    (repo / "Management Pack" / "app" / "other").mkdir()
    (repo / "Management Pack" / "app" / "other" / "tls.py").write_text("x\n", encoding="utf-8")
    found, how = review.resolve("tls.py", files_of(repo))
    assert found is None
    assert how.startswith("ambiguous")


def test_resolve_reports_a_missing_file(repo):
    assert review.resolve("tools/validate/review.ps1", files_of(repo)) == (None, "missing")


def test_citation_in_range_passes_and_shows_the_line(repo):
    page = write_page(repo, "2026-01-01-review.md", "See `utils/tls.py:2` for the function.\n")
    rows = review.check_citations([str(page.relative_to(repo))], files_of(repo), root=repo)
    assert len(rows) == 1
    _, number, cited, status, detail = rows[0]
    assert (number, cited, status) == (1, "utils/tls.py:2", "PASS")
    assert "def publish():" in detail


def test_citation_past_the_end_of_the_file_fails(repo):
    page = write_page(repo, "2026-01-01-review.md", "Old line `utils/tls.py:40-45`.\n")
    rows = review.check_citations([str(page.relative_to(repo))], files_of(repo), root=repo)
    assert rows[0][3] == "FAIL"
    assert "3 lines" in rows[0][4]


def test_citation_to_a_missing_file_fails(repo):
    page = write_page(repo, "2026-01-01-review.md", "Script `tools/validate/review.ps1` does this.\n")
    rows = review.check_citations([str(page.relative_to(repo))], files_of(repo), root=repo)
    assert (rows[0][2], rows[0][3]) == ("tools/validate/review.ps1", "FAIL")


def test_citations_inside_code_fences_are_ignored(repo):
    page = write_page(repo, "2026-01-01-review.md", "```\n`tools/nothere.ps1`\n```\n")
    assert review.check_citations([str(page.relative_to(repo))], files_of(repo), root=repo) == []


# ---------------------------------------------------------------- tables

def test_finding_ids_come_from_the_first_column_only():
    text = (
        "| ID | Severity | Finding |\n"
        "| :--- | :---: | :--- |\n"
        "| SEC-01 | Medium | Uses UTF-8 text |\n"
        "| N-01 | Medium | A new finding |\n"
        "Plain text mentions BUG-09 but is not a table row.\n"
    )
    assert set(review.finding_ids(text)) == {"SEC-01", "N-01"}


def test_decisions_read_the_decision_column_by_its_header():
    text = (
        "| ID | Decision | Action taken |\n"
        "| :--- | :--- | :--- |\n"
        "| BUG-01 | Implemented | Timeout added. Issue #53. |\n"
        "| BUG-02 | Partly | Only the docs changed. |\n"
    )
    done = review.decisions(text)
    assert done["BUG-01"][0] == "Implemented"
    assert done["BUG-01"][1] == "Timeout added. Issue #53."
    assert done["BUG-02"][0] == "Partly"


def test_a_table_ends_at_the_first_line_that_is_not_a_row():
    text = (
        "| ID | Decision | Action taken |\n"
        "| :--- | :--- | :--- |\n"
        "| BUG-01 | Implemented | Issue #1 |\n"
        "\n"
        "| BUG-02 | Implemented | Issue #2 |\n"
    )
    assert "BUG-02" not in review.decisions(text)


def test_a_repeated_decision_row_is_marked_as_a_duplicate():
    text = (
        "| ID | Decision | Action taken |\n"
        "| :--- | :--- | :--- |\n"
        "| BUG-01 | Implemented | Issue #1 |\n"
        "| BUG-01 | Deferred | Later |\n"
    )
    assert review.decisions(text)["BUG-01"][3] is True


# ---------------------------------------------------------------- trace

def review_page(*rows):
    return "\n".join(["| ID | Severity | Finding |", "| :--- | :--- | :--- |", *rows]) + "\n"


def response_page(*rows):
    return "\n".join(["| ID | Decision | Action taken |", "| :--- | :--- | :--- |", *rows]) + "\n"


def trace(repo):
    return review.check_trace(repo / REVIEW_DIR, repo)


def statuses(rows):
    return [(status, message) for status, _, _, message in rows]


def test_a_finding_with_no_decision_fails(repo):
    write_page(repo, "2026-01-01-review.md", review_page("| BUG-01 | High | Hangs |", "| BUG-02 | Low | Typo |"))
    write_page(repo, "2026-01-01-completed.md", response_page("| BUG-01 | Implemented | Issue #1 |"))
    rows = trace(repo)
    assert ("FAIL", "BUG-02 has no decision in the response page") in statuses(rows)


def test_an_unknown_decision_value_fails(repo):
    write_page(repo, "2026-01-01-review.md", review_page("| BUG-01 | High | Hangs |"))
    write_page(repo, "2026-01-01-completed.md", response_page("| BUG-01 | Maybe | Issue #1 |"))
    assert any(s == "FAIL" and "'Maybe' is not one of" in m for s, m in statuses(trace(repo)))


def test_implemented_without_an_issue_commit_or_test_is_a_warning(repo):
    write_page(repo, "2026-01-01-review.md", review_page("| BUG-01 | High | Hangs |", "| BUG-02 | High | Hangs |"))
    write_page(repo, "2026-01-01-completed.md", response_page(
        "| BUG-01 | Implemented | Done, see Issue #7 |",
        "| BUG-02 | Implemented | Fixed, and a test covers it in tests/test_x.py |",
        "| BUG-03 | Implemented | Done |",
    ))
    rows = statuses(trace(repo))
    assert not any("BUG-01" in m for _, m in rows)
    assert not any("BUG-02" in m for _, m in rows)
    assert ("WARN", "BUG-03 is Implemented, but the action names no issue, commit or test") in rows


def test_a_commit_hash_counts_as_evidence(repo):
    write_page(repo, "2026-01-01-review.md", review_page("| BUG-01 | High | Hangs |"))
    write_page(repo, "2026-01-01-completed.md", response_page("| BUG-01 | Implemented | Fixed in 1e0a1cb |"))
    assert not any("BUG-01" in m for _, m in statuses(trace(repo)))


def test_a_rejected_or_deferred_item_must_return_in_a_later_review(repo):
    write_page(repo, "2026-01-01-review.md", review_page("| SEC-03 | Medium | SHA-1 |", "| GOV-04 | Low | Tags |"))
    write_page(repo, "2026-01-01-completed.md", response_page(
        "| SEC-03 | Rejected | Limit of vCenter |", "| GOV-04 | Deferred | Later |"))
    write_page(repo, "2026-02-01-review.md", review_page("| SEC-03 | Medium | Still SHA-1 |"))
    rows = statuses(trace(repo))
    assert ("WARN", "GOV-04 (Deferred) is not mentioned in any later review") in rows
    assert not any("SEC-03 (Rejected)" in m for _, m in rows)


def test_a_review_without_a_response_page_is_information_only(repo):
    write_page(repo, "2026-10-30-review.md", review_page("| N-01 | Medium | New |"))
    rows = trace(repo)
    assert [r[0] for r in rows] == ["INFO"]
    assert "no response page yet" in rows[0][3]


def test_a_response_page_with_no_review_is_a_warning(repo):
    write_page(repo, "2026-03-01-completed.md", response_page("| BUG-01 | Implemented | Issue #1 |"))
    assert ("WARN", "response page has no review page with the same date") in statuses(trace(repo))


def test_a_decision_for_an_unknown_id_is_a_warning(repo):
    write_page(repo, "2026-01-01-review.md", review_page("| BUG-01 | High | Hangs |"))
    write_page(repo, "2026-01-01-completed.md", response_page(
        "| BUG-01 | Implemented | Issue #1 |", "| BUG-99 | Implemented | Issue #2 |"))
    assert ("WARN", "BUG-99 is not in any review page") in statuses(trace(repo))


# ---------------------------------------------------------------- claims and report

def test_claims_list_python_versions_and_pass_counts(repo):
    write_page(repo, "2026-01-01-completed.md", "Tests: 476 passed on Python 3.12.10.\n")
    rows = review.check_claims(repo / REVIEW_DIR, snapshot={"tests_collected": 486})
    claims = [r[2] for r in rows]
    assert "476 passed" in claims
    assert "Python 3.12.10" in claims
    assert "snapshot collected 486 tests" in [r[3] for r in rows]


def test_the_report_summarises_failures(repo):
    report = review.markdown(None, [("p.md", 3, "x.py:9", "FAIL", "line out of range")],
                             [("FAIL", "p.md", 4, "BUG-02 has no decision")], [], None)
    assert "**Summary:** 2 FAIL, 0 WARN." in report
    assert "## 1. Citations" in report and "## 3. Stated claims" in report
