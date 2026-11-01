#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""strata-ci compare -- is the difference between two recorded runs larger than the noise?

Reads two run JSONs written by bench.py and answers one question only:
did B move more than 2x the pooled coefficient of variation?

Why 2x: the runs here measure CV ~1.1% when warm.  A gate at the CV itself would fire on
noise half the time; at 2x it misses sub-1% effects (which need a microbenchmark, not the
engine) and keeps the signal honest.

Usage: compare.py <run_a.json | run_id> <run_b.json | run_id> [--by tok_s]
"""
import json
import os
import sys

RUNS = "/home/albus/strata166/ci/state/runs"


def load(name):
    p = name if os.path.exists(name) else os.path.join(RUNS, name + ".json")
    if not os.path.exists(p):
        raise SystemExit("no such run: %s" % name)
    with open(p) as f:
        return json.load(f)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    key = "tok_s"
    if "--by" in sys.argv:
        key = sys.argv[sys.argv.index("--by") + 1]
    a, b = load(sys.argv[1]), load(sys.argv[2])

    ma, mb = a["metrics"][key], b["metrics"][key]

    # A run whose own spread is huge is not evidence: the first request after an idle spell
    # can be 2.3x slower (30.5 vs 69.5 tok/s measured), which pushes CV to ~18%.  Comparing
    # against such a run would either hide a real effect or invent one.  Refuse it instead
    # of widening the threshold -- widening is how "noise" becomes an excuse.
    BAD_CV = 10.0
    bad = [(r["run_id"], r["metrics"][key]["cv_pct"])
           for r in (a, b) if (r["metrics"][key]["cv_pct"] or 0) > BAD_CV]
    if bad:
        print("RUN UNUSABLE -- spread too wide to compare:")
        for rid, cv in bad:
            print("  %-40s CV %.2f%% > %.0f%%" % (rid, cv, BAD_CV))
        print("\nwarm the engine (discard >=2 samples) and re-run bench, then compare again.")
        return 4

    delta = mb["median"] - ma["median"]
    pct = 100.0 * delta / ma["median"] if ma["median"] else 0.0
    cv = max(ma["cv_pct"] or 0.0, mb["cv_pct"] or 0.0)
    threshold = 2 * cv
    verdict = "REAL" if abs(pct) > threshold else "NOISE (do not report as a result)"

    print("A: %-40s %s" % (a["run_id"], a.get("git_tag") or a.get("git_head", "")[:10]))
    print("   exe=%s env=%d median %s = %.2f (CV %.2f%%, n=%d)"
          % (a["exe"], len(a.get("env") or {}), key, ma["median"], ma["cv_pct"], ma["n"]))
    print("B: %-40s %s" % (b["run_id"], b.get("git_tag") or b.get("git_head", "")[:10]))
    print("   exe=%s env=%d median %s = %.2f (CV %.2f%%, n=%d)"
          % (b["exe"], len(b.get("env") or {}), key, mb["median"], mb["cv_pct"], mb["n"]))
    print()
    print("delta = %+.2f %s (%+.2f%%)" % (delta, key, pct))
    print("noise = 2 x CV = %.2f%%" % threshold)
    print("verdict: %s" % verdict)

    # what differed, so a "REAL" result can be attributed
    print()
    print("--- what changed between the two runs ---")
    for field in ("git_head", "exe_md5", "cfg_md5", "exe"):
        if a.get(field) != b.get(field):
            print("  %-8s %s -> %s" % (field, str(a.get(field))[:16], str(b.get(field))[:16]))
    ea, eb = a.get("env") or {}, b.get("env") or {}
    for k in sorted(set(ea) | set(eb)):
        if ea.get(k) != eb.get(k):
            print("  env.%-34s %s -> %s" % (k, ea.get(k, "<unset>"), eb.get(k, "<unset>")))
    if a.get("workload") != b.get("workload"):
        print("  workload differs: %s vs %s" % (a.get("workload"), b.get("workload")))

    return 0 if verdict == "REAL" else 3


if __name__ == "__main__":
    sys.exit(main())
