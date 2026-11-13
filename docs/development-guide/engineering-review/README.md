# Engineering Review

The engineering review is a dated audit of the pack: the adapter code, the tooling, the repository and the documentation, and how well the pack fits VCF Operations 9. It records what was found, what was done about each finding, and whether the fix holds.

This page explains why the reviews exist, what they cover, how a review is made and how to check its evidence. The findings are in the dated pages listed below.

## Why it is kept

- **Each finding has an ID.** A finding can be tracked, closed or challenged one at a time, in the same way in every review.
- **Each finding has a decision.** The response page says what was done, or why nothing was done. No finding is dropped silently.
- **Each decision is challenged.** A later re-score checks each rejection and deferral against its reason, and checks the fixes against the code.
- **Each citation points to code.** A reader can open the file and line that a finding names.
- **The record is dated.** A reader sees what the code looked like when the review was made, and what changed afterwards.

The review is not a test plan, a release gate or a list of bugs. Bugs that need fixing are GitHub issues. Planned work is on the [To Do project](https://github.com/users/e1-rahabok/projects/1). The review explains why the work matters and records what was decided.

## Pages

| Page | What it is |
| :--- | :--- |
| [29 Oct 2026 Review](2026-10-29-review.md) | The review of version 0.6.12: a scorecard, a verdict, and each finding with its severity, location and recommendation. |
| [29 Oct 2026 Completed](2026-10-29-completed.md) | The response to that review: the decision and the action for each finding, and the open items. |
| [30 Oct 2026 Review](2026-10-30-review.md) | The re-score after the 0.7.0 fixes: each fix checked against the code, each rejection and deferral given a verdict, and new findings. |

## Scope

A review covers:

- **Adapter code** in `Management Pack/app`: collection, metrics, guest operations, TLS, configuration files and the Suite API reads.
- **Tooling** in `tools/`: the scripts that build, install, validate and document the pack.
- **Repository and governance:** CI, dependency pins, the container image, ignore rules, templates and ownership files.
- **Documentation:** whether the pages match the code, and whether the index is complete.
- **Fit with VCF Operations 9:** the product behaviour that the pack depends on.

A review does not cover, unless the page says so:

- **Live behaviour** on a vCenter or VCF Operations instance. The review may note that a check is still open.
- **Reproduction of every bug.** A finding that was only read says so.
- **Performance measurements**, unless the page includes them.

Each page states its own scope, what was done and what was not done. Read that section before relying on a finding.

## How a review is made

A review has three stages. Each stage is its own page.

1. **Review.** Read the code and the docs for the scope. Record each finding with an ID, a severity, a location and a recommendation. Score each area. Mark each finding that was only read.
2. **Response.** The owner of the code decides each finding: `Implemented`, `Partly`, `Deferred`, `Rejected` or `No change`. For each one, the response names the action, and the issue, commit or test that shows it.
3. **Re-score.** After the fixes are in, a later review checks the response. It checks each implemented fix against the code. It gives a verdict on each rejection and deferral, and records new findings.

Pages are named by date and kind: `YYYY-MM-DD-review.md`, `YYYY-MM-DD-completed.md`. A re-score is also a `-review.md` page, dated when it was written.

## How to run a review

The steps below are the process. The review itself is a judgment that a reviewer makes. The evidence tool checks that the record is complete and traceable. It does not make the judgment.

1. **Set the scope.** Name the version or commit, the folders, and what is excluded. Write it at the top of the page.
2. **Read the code and the docs.** Read the entry points first, then the parts the scope names. Check every claim against the file it names.
3. **Write the findings.** Give each one an ID in the first column of a table. Give each citation as `` `path:line` ``. Mark any finding that was not reproduced.
4. **Score the areas.** Use the same areas as the previous review, so the scores can be compared.
5. **Check the evidence.** Run the evidence tool. It reports broken citations and recorded facts, and it shows the stated test counts next to the measured ones.

   ```bash
   python tools/review/review.py check
   python tools/review/review.py check --rev <commit the review was made on>
   ```

   The tool, its options and its limits are in [Review Evidence Tool](../../../tools/review/review.md).

6. **Get the response.** The owner fills in the response page. Each finding needs one decision. For `Implemented`, the action names the issue, commit or test. Run the tool again to check the response.
7. **Re-score later.** After the fixes are released or validated, write a re-score. Check each implemented fix. Give a verdict on each rejection and deferral. Record new findings. Update the scores.
8. **Keep the snapshot.** Save the output of `python tools/review/review.py snapshot --out <file>` with the review, so a later reader knows what the numbers were measured against.

Keep one review page per date. Do not edit an earlier review to match a later decision. Write a new page instead, so the record shows what was known at each date.

## Reading a review

- Start with the scorecard and the verdict. They say what the review concluded.
- Read the findings table for the area you care about. Each finding gives a location, so you can check it.
- Read the response page for the decisions. A `Deferred` or `Rejected` item is an open question, and the later re-score says whether the reason still holds.
- A finding that was only read says so. Treat it as a lead to check, not a confirmed defect.
- Check the date of the code. A line number in a review refers to the code as it was on that date.

## Related

- [Tests](../tests.md): the unit tests, the link check and the live validation.
- [Tools](../../../tools/README.md): the scripts in the repository, including the evidence tool.
- [Contributing](../../../CONTRIBUTING.md): how a change is proposed and reviewed.
