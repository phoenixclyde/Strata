#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1040: pull the R104 window arm files and rebuild the A/B table locally (per-run CV, not cross-run).
Emits the deploy-gate A/B evidence file with target_kind=capacity."""
import io, json, os, sys, statistics as st
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

W = r"D:/workbuddy_space/strata_ws/albus/w1040"
os.makedirs(W, exist_ok=True)
FILES = ["arm_kvgA.json", "arm_kvgA2.json", "arm_kvgB.json", "arm_kvgB2.json"]
for f in FILES:
    loc = os.path.join(W, "data", f)
    os.makedirs(os.path.dirname(loc), exist_ok=True)
    ok, size, md5, det = _sshutil.fetch_b64("/home/albus/strata166/tmp/w1039/" + f, loc)
    print(f, ok, size, md5)


def per_target(d):
    o = {}
    for r in d.get("prefill", []):
        o.setdefault(r["target"], []).append(r["gpu_ms"] * 1000.0 / max(r["tokens"], 1))
    return o


def load(n):
    return json.load(io.open(os.path.join(W, "data", n), encoding="utf-8"))


A = [load("arm_kvgA.json"), load("arm_kvgA2.json")]
B = [load("arm_kvgB.json"), load("arm_kvgB2.json")]
pa = [per_target(d) for d in A]
pb = [per_target(d) for d in B]

print("\n%-7s %10s %10s %8s %10s %8s" % ("target", "A us/tok", "B us/tok", "delta", "2xCV(run)", "n"))
rows = []
for t in sorted(set(pa[0]) & set(pb[0])):
    ra = [st.mean(d[t]) for d in pa if t in d]
    rb = [st.mean(d[t]) for d in pb if t in d]
    ma, mb = st.mean(ra), st.mean(rb)
    # per-arm CV from that arm's own runs (never pooled across arms)
    cvs = []
    for xs in (ra, rb):
        if len(xs) > 1:
            cvs.append(100.0 * st.stdev(xs) / st.mean(xs))
    cv = max(cvs) if cvs else 0.0
    delta = 100.0 * (mb - ma) / ma
    print("%-7d %10.1f %10.1f %+7.2f%% %9.2f%% %4d/%d" % (t, ma, mb, delta, 2 * cv, len(ra), len(rb)))
    rows.append({"name": "prefill_%d" % t, "n": min(len(ra), len(rb)),
                 "mean_base": round(ma, 2), "mean_cand": round(mb, 2), "cv_pct": round(cv, 2)})

dec = []
for arm, lbl in ((A, "A"), (B, "B")):
    xs = [r["tok_s"] for d in arm for r in d.get("decode", [])]
    dec.append((lbl, xs, st.mean(xs) if xs else 0))
print("\ndecode tok/s: " + " | ".join("%s n=%d mean=%.2f" % (l, len(x), m) for l, x, m in dec))

ab = {
    "target": "expert_cache_slots",
    "target_kind": "capacity",
    "capacity": {"base_slots": 7463, "cand_slots": 8301,
                 "base_line": "strata generate: expert cache 7463 slots, 21.79 GiB of VRAM",
                 "cand_line": "strata generate: expert cache 8301 slots, 24.23 GiB of VRAM"},
    "baseline": {"n": 4, "mean": 7463, "cv_pct": 0.0},
    "candidate": {"n": 4, "mean": 8301, "cv_pct": 0.0},
    "guard": rows,
    "numeric": {"mode": "bitident", "note": "prompt-path fp32 logits, 1000 and 20000 tokens, byte-compared (see kl.txt)"},
    "source": "tmp/w1039/arm_kvg{A,A2,B,B2}.json (window 13:42-13:53)",
}
out = os.path.join(W, "ab_kvg.json")
io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(ab, ensure_ascii=False, indent=1))
print("\nwrote", out)
