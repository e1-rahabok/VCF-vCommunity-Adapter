# KPI Equivalence Test

Use this test when you restructure KPI code and the KPI values must stay the same. It runs the same planned cases through two copies of the code, before and after the change, and compares what each one publishes.

It does not test whether a KPI is correct. The unit tests (`python -m pytest tests`) do that, with worked examples. This test only answers one question: does the new code give the same values as the old code?

## What it covers

About 3,400 cases. Each case is named after what it covers, and goes through the entry point the adapter calls (`collect_..._metrics`), with the fake VCF Operations in `Management Pack/tests/fakes.py`. The test compares what gets published, plus the row values.

| KPI | Cases |
| :--- | :--- |
| Cluster Risk | Each of the 12 rows at 0, at every band limit, just below and just above each limit, mid-band and beyond the end. No data. DRAM at 0 or missing, with and without the fallback. Cores or threads missing or 0. VMs without a size. The Monster VM settings at default, minimum, maximum and invalid values. The highest host, ties, and hosts without data. All rows together, in every combination of two bands. |
| Cluster Performance, ESXi Performance | Each VM stat at every planned value, for its worst-VM and 90th-percentile rows. 0 to 30 VMs, covering where the 90th-percentile position changes, in any order, with ties. VMs without stats. Bad network packets at every planned value, each counter missing, no packets, several hosts. All rows together. |
| VM Performance, Guest OS Performance | Each row at every planned value. No data. Each input of a calculated row missing, or its divisor at 0. All rows together. |
| Cluster Consumption | Every host state, against each kind of Usable Capacity. All hosts down. Every way Usable Capacity can be reported. Each row at every planned value. Each host stat missing. The NVMe tier. |

The cases are in `planned_cases.py`. A new row is covered automatically once it is in the KPI's row table. A new kind of input needs a new case.

## How to run it

From the repository root, with the Python that runs the unit tests:

1. Get a copy of the code from before the change, for example from `main`:

   ```
   git worktree add ../before main
   ```

2. Run the cases on both copies:

   ```
   python tools/equivalence/planned_cases.py ../before/"Management Pack"/app "Management Pack/tests" before.json
   python tools/equivalence/planned_cases.py "Management Pack/app" "Management Pack/tests" after.json
   ```

3. Compare the results:

   ```
   python tools/equivalence/compare.py before.json after.json
   ```

   It exits 0 when every case gives the same result. When any case differs, it exits 1 and lists each difference row by row.

4. Remove the copy: `git worktree remove ../before`.

## Reading the result

- **"publish the KPI"** counts the cases that published a KPI. The `collect_..._metrics` functions never stop the collection on an error, so a broken case publishes nothing, and two copies that both publish nothing would look the same. This count shows that they do publish. The other cases are the ones built to have no data.
- **A difference is not always a bug.** When a change is meant to change values, every difference must be one that the change explains. Any other difference is a bug.
