#!/usr/bin/env python3
"""W1039/R104: compare two arms from the kvg window and print the verdict table.

  python3 summarize_kvg.py <armA.json> <armB.json>       # works on any two arm files
  python3 summarize_kvg.py --log <kvg.log>               # the elastic-K/V lines the window captured

Per target: mean us/token on the GPU timeline, CV, 2xCV, delta, and the decode arm.  Prints INCONCLUSIVE when the
delta is inside 2xCV of the candidate arm - the same rule the plan uses everywhere else.
"""
import json
import statistics as st
import sys


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def per_target(d):
    out = {}
    for r in d.get("prefill", []):
        out.setdefault(r["target"], []).append(r["gpu_ms"] * 1000.0 / max(r["tokens"], 1))
    return out


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--log":
        import re
        txt = open(sys.argv[2], encoding="utf-8", errors="replace").read()
        for pat, tag in ((r"elastic K/V: .*", "elastic K/V"),
                         (r"expert cache \d+ slots.*", "expert cache"),
                         (r"decode timing: .*CPU [\d.]+.*", "decode CPU"),
                         (r"could not map.*", "MAP FAILURE"),
                         (r"ERR the K/V could not.*", "TRIM FAILURE")):
            hits = re.findall(pat, txt)
            print("%-14s %s" % (tag, hits[-1][:220] if hits else "(none)"))
        return

    args = sys.argv[1:]
    if "--" in args:
        k = args.index("--")
        fa, fb = args[:k], args[k + 1:]
    else:
        fa, fb = [args[0]], [args[1]]
    arms_a = [load(f) for f in fa]
    arms_b = [load(f) for f in fb]

    def pool(arms):
        out = {}
        for d in arms:
            for t, xs in per_target(d).items():
                out.setdefault(t, []).extend(xs)
        return out

    pa, pb = pool(arms_a), pool(arms_b)
    # per-run means: the noise that matters is run-to-run drift, not sample-to-sample inside one run
    pa_r = [per_target(d) for d in arms_a]
    pb_r = [per_target(d) for d in arms_b]
    print("%-7s %10s %10s %8s %8s %10s %s" % ("target", "A us/tok", "B us/tok", "delta", "2xCV(run)", "n(A/B)", "verdict"))
    for t in sorted(set(pa) & set(pb)):
        ra = [st.mean(d[t]) for d in pa_r if t in d]
        rb = [st.mean(d[t]) for d in pb_r if t in d]
        ma, mb = st.mean(ra), st.mean(rb)
        runs = ra + rb
        cvr = 100.0 * st.stdev(runs) / st.mean(runs) if len(runs) > 1 else 0.0
        delta = 100.0 * (mb - ma) / ma
        verdict = "INCONCLUSIVE" if abs(delta) <= 2 * cvr else ("SLOWER" if delta > 0 else "FASTER")
        print("%-7d %10.1f %10.1f %+7.2f%% %7.2f%% %6d/%-3d %s" % (t, ma, mb, delta, 2 * cvr, len(pa[t]), len(pb[t]), verdict))
        if len(ra) > 1 or len(rb) > 1:
            print("        runs A %s | B %s" % (" ".join("%.1f" % v for v in ra), " ".join("%.1f" % v for v in rb)))

    da = [x["tok_s"] for d in arms_a for x in d.get("decode", [])]
    db = [x["tok_s"] for d in arms_b for x in d.get("decode", [])]
    if da and db:
        ma, mb = st.mean(da), st.mean(db)
        cva = 100.0 * st.stdev(da) / ma if len(da) > 1 else 0.0
        cvb = 100.0 * st.stdev(db) / mb if len(db) > 1 else 0.0
        print("\ndecode tok/s  A %.2f (cv %.1f%%, n=%d)  B %.2f (cv %.1f%%, n=%d)  delta %+.2f%%" % (
            ma, cva, len(da), mb, cvb, len(db), 100.0 * (mb - ma) / ma))
        print("(decode 2xCV band is wide: %.0f%%)" % (2 * max(cva, cvb)))


if __name__ == "__main__":
    main()
