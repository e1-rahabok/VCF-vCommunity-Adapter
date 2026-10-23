#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Planned equivalence cases for the 6 KPIs. Every case is chosen on purpose and named for what it covers.

    python tools/equivalence/planned_cases.py <app folder> <tests folder> <output.json>

Each case goes through the entry point the adapter calls (collect_..._metrics), with the fake VCF Operations of
tests/fakes.py, and records what is published plus the row values. Run it on two copies of the code, then compare
them with compare.py. See equivalence.md.
"""
import json
import sys

app, tests, out = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path[:0] = [app, tests]

import logging
logging.disable(logging.CRITICAL)

from fakes import FakeObject, FakeSuiteApi
from metrics.cluster import cluster_risk_metrics as cr
from metrics.cluster import cluster_performance_metrics as cp
from metrics.cluster import cluster_consumption_metrics as cc
from metrics.host import esxi_performance_metrics as ep
from metrics.vm import vm_performance_metrics as vp
from metrics.vm import guest_os_performance_metrics as go
from metrics import vm_contention as vc
from utils.ops_inventory import VmInfo, HostInfo

GB_KB = 1024.0 * 1024.0
cases = {}


def r(x):
    return None if x is None else round(float(x), 9)


def rd(d):
    return {k: r(v) if isinstance(v, (int, float)) or v is None else v for k, v in sorted(d.items())}


def record(label, output):
    assert label not in cases, label
    cases[label] = output


def points(metric):
    """0, every band limit, just below and just above each, the middle of each band, and beyond the end."""
    limits = [metric.best, metric.green, metric.yellow, metric.orange, metric.zero_at]
    pts = {0.0}
    for x in limits:
        eps = max(abs(x), 1.0) * 1e-6
        pts |= {x, x - eps, x + eps}
    for a, b in zip(limits, limits[1:]):
        pts.add((a + b) / 2.0)
    pts.add(max(limits) * 1.5 + 1.0)
    return sorted(p for p in pts if p >= 0)


def band_values(metric):
    """One value per band: best, then the middle of green, yellow, orange and red."""
    limits = [metric.best, metric.green, metric.yellow, metric.orange, metric.zero_at]
    return [metric.best] + [(a + b) / 2.0 for a, b in zip(limits, limits[1:])]


def api_with(samples):
    return FakeSuiteApi(samples={rid: {k: [v] for k, v in s.items()} for rid, s in samples.items()})


# =================================================================================================================
# Cluster Risk
# =================================================================================================================
D = 512 * GB_KB
MONSTER_MB = min(0.4 * D / 1024.0, 256 * 1024.0)
NAMES = [m.name for m in cr.METRICS]


def vm(i, vcpus=None, memory_mb=None, host="h1"):
    return VmInfo(f"vm{i}", f"vm{i}", f"vm-{i}", host, True, vcpus, memory_mb)


def risk_inputs(name, v, host_id="h1"):
    """(host stats, VMs) that give the row `name` the value v on a host with 32 cores and 64 threads."""
    dram = {cr.MEM_DRAM_CAPACITY: D}
    return {
        NAMES[0]: ({cr.CPU_THREAD_UTIL: v}, []),
        NAMES[1]: ({cr.CPU_THREAD_UTIL: v * 25.0, cr.CPU_CORE_UTIL: 50.0}, []),     # 2 x thread % / core %
        NAMES[2]: ({**dram, cr.MEM_CONSUMED: v / 100.0 * D}, []),
        NAMES[3]: ({**dram, cr.MEM_BALLOONED: v / 100.0 * D}, []),
        NAMES[4]: ({**dram, cr.MEM_COMPRESSED: v / 200.0 * D, cr.MEM_SWAPPED: v / 200.0 * D}, []),
        NAMES[5]: ({cr.MEM_TIERING_LATENCY: v}, []),
        NAMES[6]: ({cr.CPU_RESERVED: v * 1000.0, cr.CPU_CAPACITY: 100000.0}, []),
        NAMES[7]: ({**dram, cr.MEM_RESERVED: v / 100.0 * D}, []),
        NAMES[8]: ({cr.VCPUS_ALLOCATED: v * 32.0}, []),
        NAMES[9]: ({**dram, cr.MEM_ALLOCATED: v * D}, []),
        NAMES[10]: ({}, [vm(0, vcpus=16.0 * v, host=host_id)]),
        NAMES[11]: ({**dram}, [vm(0, memory_mb=v * MONSTER_MB, host=host_id)]),
    }[name]


def run_risk(label, hosts, stats_by_host, monster=None):
    monster = monster or cr.DEFAULT_MONSTER_VM
    obj = FakeObject("cluster")
    cr.collect_cluster_risk_metrics(obj, "cluster", hosts, api_with(stats_by_host), monster)
    record(f"risk|{label}", {"published": rd(obj.metrics),
                             "values": rd(cr.cluster_risk_values(hosts, stats_by_host, monster))})


def host(host_id="h1", cores=32.0, threads=64.0, vms=()):
    return cr.HostInventory(host_id, cores, threads, list(vms))


# Each row at every planned value, alone on one host.
for metric in cr.METRICS:
    for v in points(metric):
        stats, vms = risk_inputs(metric.name, v)
        run_risk(f"row={metric.name}|value={v!r}|band-point", [host(vms=vms)], {"h1": stats})
    # No data for the row.
    run_risk(f"row={metric.name}|no-stats", [host()], {"h1": {}})

# Divisors and host attributes.
for name in NAMES[2:5] + [NAMES[7], NAMES[9], NAMES[11]]:
    stats, vms = risk_inputs(name, 50.0 if "Ratio" not in name else 1.5)
    for variant, dram in [("dram-0-fallback", {cr.MEM_DRAM_CAPACITY: 0.0, cr.MEM_DRAM_CAPACITY_FALLBACK: D}),
                          ("dram-missing-fallback", {cr.MEM_DRAM_CAPACITY_FALLBACK: D}),
                          ("dram-both-missing", {}), ("dram-0-no-fallback", {cr.MEM_DRAM_CAPACITY: 0.0})]:
        s = {k: v for k, v in stats.items() if k not in (cr.MEM_DRAM_CAPACITY, cr.MEM_DRAM_CAPACITY_FALLBACK)}
        run_risk(f"row={name}|{variant}", [host(vms=vms)], {"h1": {**s, **dram}})
for cores, threads in [(None, 64.0), (32.0, None), (0.0, 64.0), (32.0, 0.0), (None, None)]:
    for name in [NAMES[1], NAMES[8], NAMES[10]]:
        stats, vms = risk_inputs(name, 1.5)
        run_risk(f"row={name}|cores={cores}|threads={threads}", [host(cores=cores, threads=threads, vms=vms)],
                 {"h1": stats})
run_risk("imbalance|core-util-0", [host()], {"h1": {cr.CPU_THREAD_UTIL: 50.0, cr.CPU_CORE_UTIL: 0.0}})
run_risk("cpu-reservation|capacity-0", [host()], {"h1": {cr.CPU_RESERVED: 5000.0, cr.CPU_CAPACITY: 0.0}})
run_risk("cpu-reservation|capacity-missing", [host()], {"h1": {cr.CPU_RESERVED: 5000.0}})
run_risk("zip-swap|swapped-missing", [host()], {"h1": {cr.MEM_DRAM_CAPACITY: D, cr.MEM_COMPRESSED: 1.0}})
for label, vms in [("no-vms", []), ("vm-without-size", [vm(0)]),
                   ("several-vms", [vm(0, 4.0, 4096.0), vm(1, 40.0, 300000.0), vm(2, 8.0, 1024.0)]),
                   ("vm-0-size", [vm(0, 0.0, 0.0)])]:
    run_risk(f"monster|{label}", [host(vms=vms)], {"h1": {cr.MEM_DRAM_CAPACITY: D}})

# Monster VM settings, as typed in the Adapter Instance.
for cpu in [None, "", "x", "0", "1", "50", "100", "101"]:
    for mem in [None, "x", "0", "1", "40", "100", "101"]:
        for mn in [None, "x", "0", "1", "64", "256", "100000"]:
            monster = cr.monster_vm_size(cpu, mem, mn)
            run_risk(f"monster-settings|cpu={cpu}|memory={mem}|min={mn}",
                     [host(vms=[vm(0, 20.0, 150000.0)])], {"h1": {cr.MEM_DRAM_CAPACITY: D}}, monster)

# The highest host wins, hosts without data are left out.
for metric in cr.METRICS:
    low, high = band_values(metric)[1], band_values(metric)[4]
    for label, vals in [("low-high-none", [low, high, None]), ("all-none", [None, None, None]),
                        ("ties", [high, high, low])]:
        hosts, stats = [], {}
        for i, v in enumerate(vals):
            hid = f"h{i}"
            s, vms = risk_inputs(metric.name, v, hid) if v is not None else ({}, [])
            hosts.append(host(hid, vms=vms))
            stats[hid] = s
        run_risk(f"row={metric.name}|hosts={label}", hosts, stats)


# Every row at once, so the KPI combines rows in all bands.
def risk_all(levels):
    stats, vms = {cr.MEM_DRAM_CAPACITY: D}, {"vcpus": None, "memory_mb": None}
    for metric, level in zip(cr.METRICS, levels):
        v = band_values(metric)[level]
        s, vm_list = risk_inputs(metric.name, v)
        if metric.name == NAMES[1]:
            tu = stats.get(cr.CPU_THREAD_UTIL, 50.0)
            stats[cr.CPU_CORE_UTIL] = 2.0 * tu / v if v else None
            continue
        stats.update(s)
        for one in vm_list:
            vms["vcpus"] = one.vcpus or vms["vcpus"]
            vms["memory_mb"] = one.memory_mb or vms["memory_mb"]
    stats = {k: v for k, v in stats.items() if v is not None}
    return stats, [vm(0, vms["vcpus"], vms["memory_mb"])]


for base in range(5):
    for odd in range(5):
        for i in range(len(cr.METRICS)):
            levels = [base] * len(cr.METRICS)
            levels[i] = odd
            stats, vms = risk_all(levels)
            run_risk(f"all-rows|others-band={base}|row={NAMES[i]}|band={odd}", [host(vms=vms)], {"h1": stats})


# =================================================================================================================
# Cluster Performance and ESXi Performance (the shared VM contention rows, and bad network packets)
# =================================================================================================================
STAT_KEYS = list(vc.VM_STATS)
ROW_PAIRS = {stat: names for stat, names in vc.VM_STATS.items()}
PERF_METRICS = {m.name: m for m in cp.METRICS}


def run_perf(label, vm_stats, vm_ids, packets_by_host):
    api = api_with({**vm_stats, **packets_by_host})
    host_ids = list(packets_by_host) or ["h1"]
    obj = FakeObject("cluster")
    cp.collect_cluster_performance_metrics(obj, "cluster", vm_ids, host_ids, api)
    record(f"cluster-perf|{label}", {"published": rd(obj.metrics)})
    stats = ep.read_esxi_performance_stats(api, vm_ids, host_ids[:1])
    host_obj = FakeObject("host")
    ep.collect_esxi_performance_metrics(host_obj, "host", host_ids[0], vm_ids, stats)
    record(f"esxi-perf|{label}", {"published": rd(host_obj.metrics),
                                  "values": rd(ep.esxi_performance_values(stats, host_ids[0], vm_ids))})


def packets(bad_pct=0.0, total=10000.0, drop=None):
    bad = bad_pct / 100.0 * total
    p = {vc.HOST_BAD_PACKET_STATS[0]: bad / 4, vc.HOST_BAD_PACKET_STATS[1]: bad / 4,
         vc.HOST_BAD_PACKET_STATS[2]: bad / 4, vc.HOST_BAD_PACKET_STATS[3]: bad / 4,
         vc.HOST_PACKET_STATS[0]: total / 2, vc.HOST_PACKET_STATS[1]: total / 2}
    if drop:
        p.pop(drop)
    return p


# Each VM stat at every planned value of its worst-VM row and of its 90th-percentile row.
for stat, (worst, p90) in ROW_PAIRS.items():
    for row_name in (worst, p90):
        for v in points(PERF_METRICS[row_name]):
            for n in (1, 10):
                vm_ids = [f"vm-{i}" for i in range(n)]
                run_perf(f"stat={stat}|row={row_name}|value={v!r}|vms={n}",
                         {vid: {stat: v} for vid in vm_ids}, vm_ids, {"h1": packets()})

# The 90th-percentile position, as the number of VMs changes, values in any order, and ties.
for stat in STAT_KEYS:
    for n in (0, 1, 2, 9, 10, 11, 19, 20, 21, 30):
        vm_ids = [f"vm-{i}" for i in range(n)]
        for order, values in [("ascending", list(range(n))), ("descending", list(range(n))[::-1]),
                              ("all-equal", [7.0] * n), ("two-highest-equal", list(range(n - 1)) + [n - 2] if n > 1 else [3.0] * n)]:
            run_perf(f"stat={stat}|vms={n}|order={order}",
                     {vid: {stat: float(v) * 3.0} for vid, v in zip(vm_ids, values)}, vm_ids, {"h1": packets()})
    # VMs without the stat, a VM id without any stats, stats of a VM that is not in the list.
    vm_ids = [f"vm-{i}" for i in range(10)]
    run_perf(f"stat={stat}|every-other-vm-missing", {vid: ({stat: 5.0 * i} if i % 2 else {})
                                                     for i, vid in enumerate(vm_ids)}, vm_ids, {"h1": packets()})
    run_perf(f"stat={stat}|vm-without-stats", {"vm-0": {stat: 9.0}}, ["vm-0", "vm-x"], {"h1": packets()})
    run_perf(f"stat={stat}|stats-of-vm-not-listed", {"vm-0": {stat: 9.0}, "vm-9": {stat: 99.0}}, ["vm-0"],
             {"h1": packets()})

# Bad network packets.
PACKET_METRIC = cp.METRICS[-1]
for v in points(PACKET_METRIC):
    run_perf(f"packets|value={v!r}", {}, [], {"h1": packets(v)})
for key in vc.HOST_BAD_PACKET_STATS + vc.HOST_PACKET_STATS:
    run_perf(f"packets|missing={key}", {}, [], {"h1": packets(0.3, drop=key)})
run_perf("packets|no-packets-at-all", {}, [], {"h1": packets(0.0, total=0.0)})
run_perf("packets|several-hosts", {}, [], {"h1": packets(0.1), "h2": packets(0.5), "h3": packets(0.3, drop=vc.HOST_PACKET_STATS[0])})
run_perf("packets|no-host-data", {}, [], {"h1": {}})

# Every row at once.
for base in range(5):
    for odd in range(5):
        for i, metric in enumerate(cp.METRICS):
            levels = [base] * len(cp.METRICS)
            levels[i] = odd
            vm_ids = [f"vm-{k}" for k in range(10)]
            vm_stats = {vid: {} for vid in vm_ids}
            for stat, (worst, p90) in ROW_PAIRS.items():
                worst_v = band_values(PERF_METRICS[worst])[levels[cp.METRICS.index(PERF_METRICS[worst])]]
                p90_v = band_values(PERF_METRICS[p90])[levels[cp.METRICS.index(PERF_METRICS[p90])]]
                for k, vid in enumerate(vm_ids):
                    vm_stats[vid][stat] = worst_v if k == 9 else p90_v      # 9 VMs at the p90 value, 1 worst
            pkt = band_values(PACKET_METRIC)[levels[-1]]
            run_perf(f"all-rows|others-band={base}|row={metric.name}|band={odd}", vm_stats, vm_ids, {"h1": packets(pkt)})


# =================================================================================================================
# VM Performance and Guest OS Performance
# =================================================================================================================
USED = 4 * GB_KB


def vm_inputs(name, v):
    if name == "Memory Zip Swap":
        return {vp.MEM_COMPRESSED: v / 200.0 * USED, vp.MEM_SWAPPED: v / 200.0 * USED, vp.GUEST_USED_MEMORY: USED}
    return {vp.SOURCE_STATS[name]: v}


def run_vm(label, stats):
    obj = FakeObject("vm")
    score = vp.collect_vm_performance_metrics(obj, "vm", stats)
    record(f"vm-perf|{label}", {"published": rd(obj.metrics), "score": r(score),
                                "values": rd(vp.vm_performance_values(stats))})


for metric in vp.METRICS:
    for v in points(metric):
        run_vm(f"row={metric.name}|value={v!r}|band-point", vm_inputs(metric.name, v))
    run_vm(f"row={metric.name}|no-stats", {})
for key in (vp.MEM_COMPRESSED, vp.MEM_SWAPPED, vp.GUEST_USED_MEMORY):
    s = vm_inputs("Memory Zip Swap", 1.0)
    s.pop(key)
    run_vm(f"zip-swap|missing={key}", s)
run_vm("zip-swap|guest-used-0", {vp.MEM_COMPRESSED: 10.0, vp.MEM_SWAPPED: 10.0, vp.GUEST_USED_MEMORY: 0.0})
for base in range(5):
    for odd in range(5):
        for i, metric in enumerate(vp.METRICS):
            stats = {}
            for k, m in enumerate(vp.METRICS):
                stats.update(vm_inputs(m.name, band_values(m)[odd if k == i else base]))
            run_vm(f"all-rows|others-band={base}|row={metric.name}|band={odd}", stats)


def guest_inputs(name, v):
    return {"Guest CPU Run Queue per vCPU": {go.GUEST_CPU_QUEUE: v}, "Guest Disk Queue": {go.GUEST_DISK_QUEUE: v},
            "Guest Free Memory": {go.GUEST_FREE_MEMORY_KB: v * 1024.0},
            "Guest Page-Out Rate": {go.GUEST_PAGE_OUT_RATE: v}}[name]


def run_guest(label, stats):
    obj = FakeObject("vm")
    score = go.collect_guest_os_performance_metrics(obj, "vm", stats)
    record(f"guest|{label}", {"published": rd(obj.metrics), "score": r(score),
                              "values": rd(go.guest_os_performance_values(stats))})


for metric in go.METRICS:
    for v in points(metric):
        run_guest(f"row={metric.name}|value={v!r}|band-point", guest_inputs(metric.name, v))
    run_guest(f"row={metric.name}|no-stats", {})
for base in range(5):
    for odd in range(5):
        for i, metric in enumerate(go.METRICS):
            stats = {}
            for k, m in enumerate(go.METRICS):
                stats.update(guest_inputs(m.name, band_values(m)[odd if k == i else base]))
            run_guest(f"all-rows|others-band={base}|row={metric.name}|band={odd}", stats)


# =================================================================================================================
# Cluster Consumption
# =================================================================================================================
def chost(hid, cores=32.0, conn="connected", maint="notInMaintenance", power="Powered On"):
    return HostInfo(hid, hid, hid, "cluster", cores, cores * 2 if cores else cores, conn, maint, power)


def chost_stats(cpu=40.0, dram=512.0, consumed=0.5, ballooned=0.0, compressed=0.0, swapped=0.0, drop=()):
    s = {cr.CPU_THREAD_UTIL: cpu, cr.MEM_DRAM_CAPACITY: dram * GB_KB, cr.MEM_CONSUMED: consumed * dram * GB_KB,
         cr.MEM_BALLOONED: ballooned * dram * GB_KB, cr.MEM_COMPRESSED: compressed * dram * GB_KB,
         cr.MEM_SWAPPED: swapped * dram * GB_KB}
    return {k: v for k, v in s.items() if k not in drop}


def usable(cpu_pct=80.0, mem_pct=80.0):
    s = {}
    if cpu_pct is not None:
        s.update({cc.CPU_TOTAL: 100000.0, cc.CPU_USABLE: 1000.0 * cpu_pct})
    if mem_pct is not None:
        s.update({cc.MEM_TOTAL: 1000.0 * GB_KB, cc.MEM_USABLE: 10.0 * GB_KB * mem_pct})
    return s


def run_cons(label, hosts, stats_by_host, tiers, cluster_stats):
    obj = FakeObject("cluster")
    cc.collect_cluster_consumption_metrics(obj, "cluster", hosts, stats_by_host, tiers, cluster_stats)
    record(f"consumption|{label}", {"published": rd(obj.metrics),
                                    "values": rd(cc.consumption_values(hosts, stats_by_host, tiers, cluster_stats))})


TWO = {"h1": chost_stats(), "h2": chost_stats(cpu=70.0, dram=256.0, consumed=0.9)}

# Every state of one host, next to a running host, against each kind of Usable Capacity.
for conn in ["connected", "disconnected", "notResponding", None]:
    for maint in ["notInMaintenance", "inMaintenance", "enteringMaintenance", None]:
        for power in ["Powered On", "Powered Off", "Standby", None]:
            for u_label, u in [("usable-80", usable()), ("usable-100", usable(100, 100)), ("usable-0", usable(0, 0)),
                               ("usable-missing", {})]:
                run_cons(f"host-state|conn={conn}|maint={maint}|power={power}|{u_label}",
                         [chost("h1", conn=conn, maint=maint, power=power), chost("h2", 16.0)], TWO, {}, u)

# Every host down: no host runs.
for state in [dict(maint="inMaintenance"), dict(conn="disconnected"), dict(power="Powered Off"), dict(power="Standby")]:
    for u_label, u in [("usable-0", usable(0, 0)), ("usable-80", usable()), ("usable-missing", {})]:
        tag = ",".join(f"{k}={v}" for k, v in state.items())
        run_cons(f"no-host-running|{tag}|{u_label}", [chost("h1", **state), chost("h2", 16.0, **state)], TWO, {}, u)

# Usable Capacity as reported.
for label, u in [("cpu-usable-missing", {cc.CPU_TOTAL: 1e5, cc.MEM_TOTAL: 1e9, cc.MEM_USABLE: 8e8}),
                 ("cpu-total-0", {cc.CPU_TOTAL: 0.0, cc.CPU_USABLE: 0.0, **usable(None, 80)}),
                 ("cpu-usable-negative", {cc.CPU_TOTAL: 1e5, cc.CPU_USABLE: -5.0, **usable(None, 80)}),
                 ("usable-above-total", {cc.CPU_TOTAL: 1e5, cc.CPU_USABLE: 2e5, **usable(None, 80)}),
                 ("cpu-0-memory-80", usable(0, 80)), ("cpu-80-memory-0", usable(80, 0)),
                 ("memory-missing", usable(80, None))]:
    run_cons(f"usable|{label}", [chost("h1"), chost("h2", 16.0)], TWO, {}, u)

# Each row at its planned values (both hosts the same %).
CONS = {m.name: m for m in cc.METRICS}
for v in points(CONS[cc.CPU]):
    run_cons(f"row=cpu|value={v!r}", [chost("h1"), chost("h2", 16.0)],
             {"h1": chost_stats(cpu=v * 0.8), "h2": chost_stats(cpu=v * 0.8, dram=256.0)}, {}, usable())
for name, field in [(cc.MEMORY, "consumed"), (cc.BALLOONED, "ballooned"), (cc.ZIP_SWAP, "compressed")]:
    for v in points(CONS[name]):
        frac = v / 100.0 * 0.8
        run_cons(f"row={name}|value={v!r}", [chost("h1"), chost("h2", 16.0)],
                 {"h1": chost_stats(**{field: frac}), "h2": chost_stats(dram=256.0, **{field: frac})}, {}, usable())
for v in points(CONS[cc.TIERING]):
    size = 256 * GB_KB
    tiers = {"h1": {cc.NVME_TIER_SIZE: size, cc.NVME_TIER_USAGE: v / 100.0 * 0.8 * size / 1024.0}}
    run_cons(f"row=tiering|value={v!r}", [chost("h1"), chost("h2", 16.0)], TWO, tiers, usable())

# A host missing one stat. Ballooned, compressed and swapped are the partial-memory-stat cases.
for key, cat in [(cr.CPU_THREAD_UTIL, "cpu"), (cr.MEM_DRAM_CAPACITY, "dram"), (cr.MEM_CONSUMED, "consumed"),
                 (cr.MEM_BALLOONED, "partial-memory-stat"), (cr.MEM_COMPRESSED, "partial-memory-stat"),
                 (cr.MEM_SWAPPED, "partial-memory-stat")]:
    stats = {"h1": chost_stats(ballooned=0.02, compressed=0.004, swapped=0.004, drop=(key,)),
             "h2": chost_stats(dram=256.0, ballooned=0.01, compressed=0.002, swapped=0.002)}
    run_cons(f"{cat}|missing={key}", [chost("h1"), chost("h2", 16.0)], stats, {}, usable())
run_cons("dram-fallback", [chost("h1")], {"h1": {**chost_stats(drop=(cr.MEM_DRAM_CAPACITY,)),
                                                  cr.MEM_DRAM_CAPACITY_FALLBACK: 512 * GB_KB}}, {}, usable())
run_cons("host-without-cores", [chost("h1", cores=None), chost("h2", 16.0)], TWO, {}, usable())
run_cons("no-stats-at-all", [chost("h1"), chost("h2", 16.0)], {}, {}, usable())
run_cons("tier|size-0", [chost("h1")], {"h1": chost_stats()}, {"h1": {cc.NVME_TIER_SIZE: 0.0, cc.NVME_TIER_USAGE: 5.0}}, usable())
run_cons("tier|usage-missing", [chost("h1")], {"h1": chost_stats()}, {"h1": {cc.NVME_TIER_SIZE: 1e8}}, usable())
run_cons("tier|host-down", [chost("h1", maint="inMaintenance"), chost("h2", 16.0)], TWO,
         {"h1": {cc.NVME_TIER_SIZE: 1e8, cc.NVME_TIER_USAGE: 1000.0}}, usable())

with open(out, "w") as f:
    json.dump(cases, f, sort_keys=True)
counts = {}
for label in cases:
    counts[label.split("|")[0]] = counts.get(label.split("|")[0], 0) + 1
print("cases:", counts, "total:", len(cases))
