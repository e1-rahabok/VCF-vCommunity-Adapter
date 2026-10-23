# KPI Equivalence Test

Use it when the KPI code is restructured and the KPI values must **not** change. It runs the same planned cases through two copies of the code, the one before the change and the one after, and compares what each publishes.

It is not a test of whether a KPI is right. The unit tests (`python -m pytest tests`) do that, with worked examples. This test only answers: does the new code give the same values as the old code?

## What it covers

About 3,400 cases, each chosen on purpose and named for what it covers. Every case goes through the entry point the adapter calls (`collect_..._metrics`), with the fake VCF Operations of `Management Pack/tests/fakes.py`. What is compared is what gets published, plus the row values.

| KPI | Cases |
| :--- | :--- |
| Cluster Risk | Each of the 12 rows at 0, at every band limit, just below and just above each limit, mid-band and beyond the end. No data. DRAM at 0 or missing, with and without the fallback. Cores or threads missing or 0. VMs without a size. The Monster VM settings at default, minimum, maximum and invalid values. The highest host, ties, hosts without data. All rows together, in every combination of two bands. |
| Cluster Performance, ESXi Performance | Each VM stat at every planned value, for its worst-VM and its 90th-percentile row. 0 to 30 VMs, where the 90th-percentile position changes, in any order, with ties. VMs without stats. Bad network packets at every planned value, each counter missing, no packets, several hosts. All rows together. |
| VM Performance, Guest OS Performance | Each row at every planned value. No data. Each input of a calculated row missing, or its divisor at 0. All rows together. |
| Cluster Consumption | Every host state, against each kind of Usable Capacity. All hosts down. Every way Usable Capacity can be reported. Each row at every planned value. Each host stat missing. The NVMe tier. |

The case list is in `planned_cases.py`. A new row is covered automatically when it is in the KPI's row table; a new kind of input needs a case added.

## How to run it

From the repository root, with the Python that runs the unit tests:

1. Get a copy of the code **before** the change, for example from `main`:

   ```
   git worktree add ../before main
   ```

2. Run the cases on both copies:

   ```
   python tools/equivalence/planned_cases.py ../before/"Management Pack"/app "Management Pack/tests" before.json
   python tools/equivalence/planned_cases.py "Management Pack/app" "Management Pack/tests" after.json
   ```

3. Compare:

   ```
   python tools/equivalence/compare.py before.json after.json
   ```

   It exits 0 when every case gives the same result, and 1 when any differs, then lists each difference row by row.

4. Remove the copy: `git worktree remove ../before`.

## Reading the result

- **"publish the KPI"** counts the cases that published a KPI. The `collect_..._metrics` functions never stop the collection on an error, so a broken case publishes nothing. If both copies publish nothing, they would look the same: this column shows they do publish. The rest are the cases built to have no data.
- **A difference is not always a bug.** When a change is meant to change values, each difference must be one the change explains. Anything else is a bug.
