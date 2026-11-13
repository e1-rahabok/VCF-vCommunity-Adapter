# Review Evidence Tool

`review.py` checks the evidence in the [Engineering Review](../../docs/development-guide/engineering-review/README.md) pages. It checks that each citation points to code that exists, that each finding has a recorded decision, and that each decision names its evidence. It also lists the test counts and Python versions the pages state, next to the values measured now.

It does not judge the code. A reviewer still decides what is a defect, how severe it is, and whether a fix is right.

It is read-only and is not part of CI. Run it by hand when you write or update a review page.

## Requirements

- Python 3. Only the standard library is used.
- `git`, in the repository.
- For `snapshot` and `check --snapshot`: pytest for the test count. Install the pack's requirements to collect all tests. Without them the count is left out and the snapshot says why.
- For `snapshot --linters`: `ruff`, `bandit` and `pip-audit`. A linter that is not installed is reported as `not installed`.

Run the tool with the Python that runs the unit tests. The test count and the claims check then use the same environment.

## Commands

From the repository root:

```bash
# Check the review pages against the working tree
python tools/review/review.py check

# Check the cited code as it was at the commit the review was made on
python tools/review/review.py check --rev 34e3684

# Record the facts a review depends on, as JSON
python tools/review/review.py snapshot --out review-snapshot.json

# Check the pages against a snapshot, and write the report to a file
python tools/review/review.py check --snapshot review-snapshot.json --out review-report.md
```

| Option | For | What it does |
| :--- | :--- | :--- |
| `--rev REV` | `check` | Reads the code each citation names at this commit. The review pages are still read from the working tree. |
| `--snapshot FILE` | `check` | Adds the measured test count to the claims section. |
| `--out FILE` | both | Writes the output to a file instead of printing it. |
| `--linters` | `snapshot` | Also runs `ruff`, `bandit` and `pip-audit`. This is slow. |
| `--fail` | `check` | Exits with `1` when the report has a FAIL. Meant for a person who wants a yes or no. CI does not use it. |

Without `--out`, the output goes to the screen. The tool writes no other file. It runs `git` for read-only commands, and it collects tests without writing bytecode or a pytest cache.

## What `check` reports

The report has three sections.

### 1. Citations

Every backticked file name in a review page, such as `` `utils/tls.py:118-120` ``, is looked up.

| Result | Meaning |
| :--- | :--- |
| `PASS` | The file exists. With a line number, the line exists, and the report shows its text. |
| `FAIL` | The file does not exist, or the line is past the end of the file. |
| `WARN` | The bare name matches more than one file, so the tool cannot tell which one is meant. |

A file is looked up from the repository root, then from `Management Pack/`, `Management Pack/app/` and the engineering review folder. A bare name, such as `vmService.py`, is matched by name when only one tracked file has it.

Check the text shown for each line. The tool confirms that the line exists. It does not confirm that the line still says what the review says.

### 2. Findings, decisions and re-reviews

The tool pairs each review page with the response page of the same date, such as `2026-10-29-review.md` and `2026-10-29-completed.md`.

| Result | Meaning |
| :--- | :--- |
| `FAIL` | A finding ID in the review has no decision in the response page. |
| `FAIL` | A decision is not one of `Implemented`, `Partly`, `Deferred`, `Rejected` or `No change`. |
| `FAIL` | An ID has two decision rows. |
| `WARN` | A decision is `Implemented`, but the action names no issue (`#53`), no commit (`1e0a1cb`) and no test (`tests/...` or `test_...`). |
| `WARN` | A `Partly`, `Deferred` or `Rejected` decision is not mentioned in any later review page. |
| `WARN` | A decision is for an ID that no review page lists. |
| `WARN` | A response page has no review page with the same date. |
| `INFO` | A review page has no response page yet. It lists how many IDs are new. |

A later review page that re-scores an item, such as the 30 Oct re-score, counts as a mention. The tool does not check that the re-score says the right thing about it.

### 3. Stated claims

The tool lists each Python version and each `N passed` count that the pages state, with its line. It shows the measured test count next to the pass counts when a snapshot is given.

These values are not judged. A page can state a count from a different machine on purpose, such as a local run on Python 3.12.10 next to a CI run on 3.12.15. The reader compares them.

## Why the tool checks with `--rev`

A review describes the code as it was when the review was made. Later commits move the lines. Without `--rev`, a citation can fail only because the file moved, and not because the review was wrong.

For example, the 29 Oct review was made on the 0.6.12 code. Against that commit, its line citations resolve. Against the current code, several of them are out of range. Both results are true, and the report should say which commit it checked against.

A citation to a file that was added later, such as a page written after the review, fails when `--rev` points to an older commit. That is expected.

## The snapshot

`snapshot` writes the facts that a review depends on, as JSON. Keep it with the review, so a later reader knows what the numbers were measured against.

| Field | What it is |
| :--- | :--- |
| `commit`, `branch`, `uncommitted_changes` | The git state. `uncommitted_changes` is `true` when the working tree has changes. |
| `pack_version` | The version in `Management Pack/manifest.txt`. |
| `tool_python`, `ci_python` | The Python that ran the tool, and the one the CI workflow names. |
| `tests_collected`, `tests_collected_note` | The number of unit tests pytest collects, and whether collection finished. |
| `app_python_files`, `app_python_lines` | The size of `Management Pack/app`. |
| `pattern_counts` | How many lines of `app` match each risky pattern: unbounded `while True`, bare `except`, `shell=True`, `eval`/`exec`, `pickle`/`yaml.load`, certificate checks off, `noqa`/`nosec` markers, `TODO`/`FIXME`, and `print(`. A count is a prompt to look, not a defect. |
| `docs_pages`, `broken_links` | The Markdown pages in `docs/`, and the result of the link checker. |
| `linters` | Only with `--linters`: each linter's status and last lines. |

The pattern counts are plain text searches. A match in a comment or a string counts too.

## Example

On a clean tree, `check` prints the three sections. The citation section for the 29 Oct review looks like this:

```
| Page | Line | Cited | Result | Detail |
| :--- | ---: | :--- | :--- | :--- |
| 2026-10-29-review.md | 143 | `tools/validate/review.ps1` | FAIL | missing |
| 2026-10-29-review.md | 151 | `properties/vm/vmService.py:132` | FAIL | line out of range, file has 103 lines |
```

The first row is a file the review names that does not exist. The second is a line that has moved since the review.

## Using it in a review

1. Write or update the review page. Give every citation as `` `path:line` ``, and every finding an ID in a table's first column.
2. Run `check`. Fix each `FAIL` in the review page, or record why it is right.
3. Record each decision in the response page. For `Implemented`, name the issue, the commit or the test.
4. Run `check --rev <commit>` on the commit the review was made on, to confirm the citations resolve there.
5. Run `snapshot --out` and keep the JSON with the review.

The tool does not decide whether a `WARN` is a problem. A `WARN` asks for a look.

## Tests

`Management Pack/tests/test_review_tool.py` runs the tool's functions against small fake repositories. Run it with the other unit tests:

```
cd "Management Pack"
python -m pytest tests
```

The tests do not read the real review pages, so they still pass when a review changes.

## Limits

- It finds a citation to a file or line. It does not check the meaning of the line.
- It reads a decision from a table row. A decision given only in prose is not seen.
- It can read a finding ID only from a table's first column.
- The `Implemented` evidence check looks for words and patterns. It cannot tell whether the named test covers the finding.
- The claims section does not judge any value.
- `snapshot` measures the code as it is now. It does not measure the code a review was made on, unless you check out that commit first.
- Only the `.py`, `.ps1`, `.md`, `.cfg`, `.xml`, `.json`, `.txt`, `.yml`, `.yaml`, `.csv`, `.sh`, `.toml` and `.ini` file types are cited. A citation to another type is not checked.

For the review process and the pages that the tool checks, see the [Engineering Review](../../docs/development-guide/engineering-review/README.md).
