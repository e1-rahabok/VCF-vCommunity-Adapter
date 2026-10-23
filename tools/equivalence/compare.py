#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Compare the planned cases of two copies of the code, written by planned_cases.py.

    python tools/equivalence/compare.py <before.json> <after.json>

Prints, per KPI: the number of cases, how many publish something and the KPI (so a case that fails silently in both
copies cannot pass unnoticed), and how many differ. Then every difference, row by row. Exits 1 when any case differs.
"""
import json
import sys

KPIS = ["risk", "cluster-perf", "esxi-perf", "vm-perf", "guest", "consumption"]


def main() -> int:
    before, after = (json.load(open(path, encoding="utf-8")) for path in sys.argv[1:3])
    if before.keys() != after.keys():
        print("The two files do not have the same cases: run the same planned_cases.py on both copies.")
        return 1

    print(f"{'KPI':13} {'cases':>6} {'publish something':>18} {'publish the KPI':>16} {'differ':>7}")
    differences = []
    for kpi in KPIS:
        labels = [label for label in after if label.startswith(kpi + "|")]
        some = sum(1 for label in labels if after[label]["published"])
        with_kpi = sum(1 for label in labels if any(key.endswith("Score") for key in after[label]["published"]))
        differ = [label for label in labels if before[label] != after[label]]
        differences += differ
        print(f"{kpi:13} {len(labels):6} {some:18} {with_kpi:16} {len(differ):7}")

    for label in sorted(differences):
        print(f"\n{label}")
        for part in ("published", "values"):
            old, new = before[label].get(part, {}), after[label].get(part, {})
            for key in sorted(set(old) | set(new)):
                if old.get(key) != new.get(key):
                    print(f"   {part:9} {key.split('|')[-1]:42} before={old.get(key)}  after={new.get(key)}")
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main())
