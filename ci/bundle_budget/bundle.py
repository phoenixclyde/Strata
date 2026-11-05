#!/usr/bin/env python3
"""bundle_budget -- the 5% gate cannot be passed one item at a time any more; this is the ledger
that says how far a *bundle* of them is from it.

Why this exists (W1013).  The plan's adoption rule is "prefill@2K >= 5%".  Every remaining
candidate on this card now measures 2-3%: down-only weight repack -3.2% (of prefill), hiding
the host plan build -2.9%, a Q8-coded v3 hyper-connection read -2.8%, a chunked GDN recurrence
-1.9%.  Applied one at a time they are all rejected by a gate they could pass together, and
the queue stalls on a rule instead of on physics.

So the rule becomes: a bundle of bit-safe items may be adopted on its *sum*, while each item
still has to clear 2x its own CV, and anything that changes rounding needs the quality gate
once for the bundle.  This script is the arithmetic, and it refuses to let the sum be typed.

  python3 ci/bundle_budget/bundle.py            # report: measured sum, estimates, distance to 5%
  python3 ci/bundle_budget/bundle.py --check    # fail if an ADOPT claim does not add up
  python3 ci/bundle_budget/bundle.py --self-test

Columns of BUNDLE.tsv (tab separated, '#' comments):

  bundle  item  mechanism  phase  phase_ms_2k  phase_delta_pct  cv_pct  basis  bit_safe  status  evidence

  phase_ms_2k   must equal the 2K cluster median of that phase in PREFILL_PHASES.tsv (this is
                the whole point: the share is never typed, it is looked up)
  phase_delta_pct  the *measured* change of that phase, negative = faster
  basis         bench   = measured at kernel/bench level, projected by the phase share
                estimate = arithmetic on a mechanism nobody has measured yet (never counted)
  status        ADOPT / CANDIDATE / REJECTED / BLOCKED
"""
from __future__ import annotations

import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PHASES = os.path.join(HERE, "..", "prefill_phases")
_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CANDIDATES = [os.path.join(PHASES, "PREFILL_PHASES.tsv"),
              os.path.join(_ROOT, "ci", "prefill_phases", "PREFILL_PHASES.tsv")] + sorted(
              __import__("glob").glob(os.path.join(_ROOT, "albus", "*", "PREFILL_PHASES.tsv")))
TSVP = os.path.join(HERE, "PREFILL_PHASES.tsv")
BUNDLE: str = os.path.join(HERE, "BUNDLE.tsv")

GATE = 5.0          # the plan's prefill@2K gate, percent
LENGTH = 2080       # the 2K cluster (measured 2083-2084 tokens)


def _phases_module():
    """phases.py lives with the TSV it produced; try this dir, then the repo, then albus/*."""
    for d in [PHASES, os.path.join(_ROOT, "ci", "prefill_phases")]:
        if os.path.exists(os.path.join(d, "phases.py")):
            sys.path.insert(0, os.path.abspath(d))
            import phases                                            # noqa: E402
            return phases
    d = sorted(__import__("glob").glob(os.path.join(_ROOT, "albus", "*", "phases.py")))
    if d:
        sys.path.insert(0, os.path.dirname(d[0]))
        import phases                                                # noqa: E402
        return phases
    raise SystemExit("phases.py not found next to PREFILL_PHASES.tsv")


def load_phases():
    """{phase: median ms} for the 2K cluster, via the same clustering phases.py uses."""
    p = _phases_module()
    path = next((x for x in CANDIDATES if os.path.exists(x)), None)
    if path is None:
        return None, "PREFILL_PHASES.tsv not found in %s" % (CANDIDATES,)
    rows = p.load_tsv(path)
    groups = p.cluster(rows)
    key = p.near(groups, LENGTH)
    if key is None:
        return None, "no cluster near %d tokens: %s" % (LENGTH, sorted(groups))
    g = groups[key]
    return {k: p.med(g, k) for k in g[0] if k != "tokens"}, None


def evidence_exists(ev):
    """The repo layout first (166 / CI), then the laptop's albus/<round>/ mirrors by basename,
    so the same BUNDLE.tsv is checkable on both without copying data around."""
    root = os.path.abspath(os.path.join(HERE, "..", ".."))
    if os.path.exists(os.path.join(root, ev)):
        return True
    import glob
    base = os.path.basename(ev)
    return bool(glob.glob(os.path.join(root, "albus", "*", base)))


def read_bundle(path=None):
    path = path or BUNDLE
    out = []
    for line in io.open(path, encoding="utf-8-sig"):      # the Windows upload carries a BOM
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        c = line.rstrip("\r\n").split("\t")
        if c[0] == "bundle":                                   # the header row
            continue
        if len(c) != 11:
            raise SystemExit("%s: %d columns, want 11: %r" % (path, len(c), c[:3]))
        out.append(dict(bundle=c[0], item=c[1], mechanism=c[2], phase=c[3],
                        phase_ms=float(c[4]), delta=float(c[5]), cv=float(c[6]),
                        basis=c[7], bit_safe=c[8], status=c[9], evidence=c[10]))
    return out


def evaluate(rows, ph, quiet=False):
    fails = []
    total = float(ph.get("gpu", 0) or 0)
    if total <= 0:
        fails.append("no gpu phase in the table: cannot derive any share")
        total = 1.0
    per = {}
    for r in rows:
        have = ph.get(r["phase"])
        if have is None:
            fails.append("%s: phase %r not in PREFILL_PHASES.tsv" % (r["item"], r["phase"]))
            continue
        if abs(r["phase_ms"] - have) > 0.02 * max(have, 1.0):
            fails.append("%s: phase_ms_2k %.1f but the table says %.1f (+-2%%)"
                         % (r["item"], r["phase_ms"], have))
        share = 100.0 * have / total
        e2e = r["delta"] * share / 100.0
        if r["basis"] == "bench" and abs(r["delta"]) < 2 * r["cv"]:
            fails.append("%s: %.2f%% is inside 2xCV (%.2f%%) - not a measurement yet"
                         % (r["item"], r["delta"], 2 * r["cv"]))
        if r["bit_safe"] not in ("Y", "N"):
            fails.append("%s: bit_safe must be Y or N" % r["item"])
        if not evidence_exists(r["evidence"]):
            fails.append("%s: evidence %s does not exist" % (r["item"], r["evidence"]))
        per.setdefault(r["bundle"], []).append(dict(r, share=share, e2e=e2e))

    adopted, estimates = {}, {}
    for b, items in per.items():
        for it in items:
            if it["status"] == "ADOPT":
                adopted[b] = adopted.get(b, 0.0) + it["e2e"]
            elif it["status"] == "CANDIDATE" and it["basis"] == "estimate":
                estimates[b] = estimates.get(b, 0.0) + it["e2e"]
        if b in adopted:
            need_quality = any(it["bit_safe"] == "N" for it in items if it["status"] == "ADOPT")
            if adopted[b] > -GATE:
                fails.append("bundle %s claims ADOPT but its measured sum is %.2f%% (gate -%.1f%%)"
                             % (b, adopted[b], GATE))
            if need_quality and not any(it["item"].startswith("Q:") for it in items):
                fails.append("bundle %s adopts a rounding-changing item without a Q: quality row" % b)

    if not quiet:
        for b in sorted(per):
            print("== bundle %s" % b)
            for it in per[b]:
                print("   %-12s %-26s phase %-22s %6.1f ms  %5.1f%% of %.0f  delta %+6.1f%% -> %+5.2f%%  [%s/%s] %s"
                      % (it["item"], it["mechanism"][:26], it["phase"][:22], it["phase_ms"], it["share"], total,
                         it["delta"], it["e2e"], it["basis"], it["status"], it["bit_safe"]))
            universe = sum(it["e2e"] for it in per[b])
            print("   -> measured sum %+.2f%% ; estimates on top %+.2f%% ; every row together %+.2f%% ; gate -%.1f%%"
                  % (adopted.get(b, 0.0), estimates.get(b, 0.0), universe, GATE))
    return fails, adopted, estimates, total


def self_test():
    ph = {"gpu": 3169.0, "gemm down": 507.0, "host grouping": 93.0}
    ok = 0
    # -40% of a 507/3169 ms phase is -6.4% of prefill, i.e. the smallest ADOPT that can legally exist
    good = [dict(bundle="B1", item="X1", mechanism="m", phase="gemm down", phase_ms=507.0,
                 delta=-40.0, cv=2.0, basis="bench", bit_safe="Y", status="ADOPT", evidence="ci/README.md")]
    f, adopted, _, _ = evaluate(good, ph, quiet=True)
    if not f:
        ok += 1
    else:
        print("  self-test MISS: a valid row was rejected: %s" % f)

    bad = [dict(good[0], phase_ms=400.0)]                      # a typed share
    f, _, _, _ = evaluate(bad, ph, quiet=True)
    if any("phase_ms_2k" in x for x in f):
        ok += 1
    else:
        print("  self-test MISS: a typed phase_ms was accepted")

    bad = [dict(good[0], delta=-2.0, cv=2.0)]                  # below 2xCV
    f, _, _, _ = evaluate(bad, ph, quiet=True)
    if any("2xCV" in x for x in f):
        ok += 1
    else:
        print("  self-test MISS: a sub-CV delta was accepted as measured")

    bad = [dict(good[0], delta=-1.0)]                          # claim without the sum
    f, _, _, _ = evaluate(bad, ph, quiet=True)
    if any("claims ADOPT" in x for x in f):
        ok += 1
    else:
        print("  self-test MISS: an ADOPT claim under the gate was accepted")

    bad = [dict(good[0], evidence="ci/nope.tsv")]
    f, _, _, _ = evaluate(bad, ph, quiet=True)
    if any("does not exist" in x for x in f):
        ok += 1
    else:
        print("  self-test MISS: a missing evidence file was accepted")

    bad = [dict(good[0], bit_safe="N", delta=-20.0)]
    f, _, _, _ = evaluate(bad, ph, quiet=True)
    if any("Q:" in x for x in f):
        ok += 1
    else:
        print("  self-test MISS: a rounding-changing ADOPT without a quality row was accepted")
    print("SELF_TEST: %d/6" % ok)
    return 0 if ok == 6 else 1


def main():
    if "--self-test" in sys.argv:
        return self_test()
    ph, err = load_phases()
    if err:
        print("BUNDLE: FAIL (%s)" % err)
        return 2
    rows = read_bundle()
    fails, adopted, estimates, total = evaluate(rows, ph)
    if fails:
        for x in fails:
            print("  FAIL " + x)
        print("BUNDLE: FAIL (%d)" % len(fails))
        return 1
    print("BUNDLE: PASS (budget %.2f/%.1f%%, estimates %+.2f%%)"
          % (sum(adopted.values()), GATE, sum(estimates.values())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
