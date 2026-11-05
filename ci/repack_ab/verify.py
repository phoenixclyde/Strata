#!/usr/bin/env python3
"""Static self-check for the repack A/B artifacts. No GPU, no network.

Runs on GitHub-hosted runners as part of Downstream gate. It does not verify
performance (that needs the GPU); it verifies that the evidence is present,
internally consistent, and that the two known W999 mistakes cannot silently
come back.
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FAILS = []


def need(cond, msg):
    if not cond:
        FAILS.append(msg)


def text(p):
    # utf-8-sig: a laptop-side editor can add a BOM; without this the first
    # comment line of RESULTS.tsv was counted as a data row (caught on first run).
    return p.read_text(encoding="utf-8-sig", errors="replace")


# 1. artifacts
for name in ("README.md", "RESULTS.tsv", "PORT_STATUS.md", "run.sh",
             "ab_bench.cu", "repack_bench.cu"):
    need((HERE / name).is_file(), "missing artifact: %s" % name)
if FAILS:
    print("VERIFY: FAIL")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)

# 2. results: four shapes, ratio agrees with the two timing columns
rows = [l for l in text(HERE / "RESULTS.tsv").splitlines()
        if l.strip() and not l.startswith("#") and not l.startswith("rows_per")]
need(len(rows) == 4, "RESULTS.tsv must carry exactly 4 measured shapes, got %d" % len(rows))
seen = []
for l in rows:
    c = l.split("\t")
    need(len(c) == 5, "bad column count: %s" % l[:60])
    if len(c) != 5:
        continue
    try:
        n, canon, rp, ratio, old = int(c[0]), float(c[1]), float(c[2]), float(c[3]), float(c[4])
    except ValueError:
        FAILS.append("non-numeric row: %s" % l[:60]); continue
    seen.append(n)
    need(abs(rp / canon - ratio) < 0.02,
         "ratio %.3f disagrees with %.3f/%.3f at rows=%d" % (ratio, rp, canon, n))
    need(canon > 0 and rp > 0, "non-positive timing at rows=%d" % n)
need(seen == [32, 128, 320, 1024], "shape order must be 32/128/320/1024, got %s" % seen)

# 3. the fair A/B must keep the two fixes that made the conclusion flip
ab = text(HERE / "ab_bench.cu")
for token in ("mmq::quantize", "q8_bytes", "repack-kernels.cuh", "Context", "hipEvent"):
    need(token in ab, "ab_bench.cu lost the fair-A/B marker %r" % token)
rp = text(HERE / "repack_bench.cu")
for token in ("use_w32", "MMQ_RP_Q8_BM", "repack_q51"):
    need(token in rp or token in ab, "dispatch marker %r missing from both benches" % token)

# 4. the port-status file must exist and name all channels (no silent "done" claim)
ps = text(HERE / "PORT_STATUS.md")
for ch in ("C1 权重上传", "C2 调度分派", "C3 激活对齐", "C5 验收", "C6 R97"):
    need(ch in ps, "PORT_STATUS.md missing channel %s" % ch)
need(re.search(r"NOT_STARTED|IN_PROGRESS|DONE", ps) is not None,
     "PORT_STATUS.md has no status column")

# 5. the gate that calls this file must still be wired in the workflow
wf = ROOT / ".github" / "workflows" / "downstream-gate.yml"
need(wf.is_file(), "downstream-gate.yml missing")
if wf.is_file():
    w = text(wf)
    need("ci/repack_ab/verify.py" in w, "workflow no longer calls verify.py")
    need("ci/round_gate.py --ci" in w, "workflow no longer calls round_gate --ci")
    need("ci/repack_ab/**" in w or "ci/**" in w, "workflow paths filter would skip ci/repack_ab")
need((ROOT / "ci" / "report_lint.py").is_file(), "ci/report_lint.py missing")
need((ROOT / "ci" / "round_gate.py").is_file(), "ci/round_gate.py missing")

# 6. W1003 width/type sweep: the production types and shapes, all three arms.
#
# Why this group exists: RESULTS.tsv holds exactly four Q5_1 shapes, which is
# not what the pack contains. On its own it let a "repack everything" plan look
# viable. This group pins the sweep that showed otherwise, and refuses a file
# whose timing columns disagree with its own ratio columns.
sw = HERE / "WIDTH_SWEEP.tsv"
need(sw.is_file(), "missing artifact: WIDTH_SWEEP.tsv")
if sw.is_file():
    s = text(sw)
    need("TIMING-ONLY" in s,
         "WIDTH_SWEEP.tsv must keep the TIMING-ONLY disclaimer (random weights)")
    need("QK_K=256" in s and "K=640" in s,
         "WIDTH_SWEEP.tsv must keep the pack mapping that explains why K-quants cannot be on down")
    srows = [l for l in s.splitlines() if l.strip() and not l.startswith("#")
             and not l.startswith("shape")]
    need(len(srows) >= 20, "WIDTH_SWEEP.tsv must carry >= 20 measured rows, got %d" % len(srows))
    combos, pts = set(), {}
    for l in srows:
        c = l.split("\t")
        need(len(c) == 10, "bad column count: %s" % l[:60])
        if len(c) != 10:
            continue
        shape, tid, tname, npr = c[0], c[1], c[2], c[3]
        try:
            canon, w32, r32, w64, r64 = (float(c[4]), float(c[5]), float(c[6]),
                                        float(c[7]), float(c[8]))
            n = int(npr)
        except ValueError:
            FAILS.append("non-numeric row: %s" % l[:60])
            continue
        combos.add((shape, tid, tname))
        pts.setdefault((shape, tid), set()).add(n)
        need(abs(w32 / canon - r32) < 0.02,
             "ratio32 %.4f disagrees with %.4f/%.4f (%s %s rows=%d)" % (r32, w32, canon, shape, tname, n))
        need(abs(w64 / canon - r64) < 0.02,
             "ratio64 %.4f disagrees with %.4f/%.4f (%s %s rows=%d)" % (r64, w64, canon, shape, tname, n))
        need(canon > 0 and w32 > 0 and w64 > 0,
             "non-positive timing (%s %s rows=%d)" % (shape, tname, n))
        best = min((canon, "canonical"), (w32, "w32"), (w64, "w64"))[1]
        need(c[9] == best,
             "recorded winner %r is not the fastest arm %r (%s %s rows=%d)"
             % (c[9], best, shape, tname, n))
    # the four production combinations, and the five row counts each
    for want in (("gu", "12", "Q4_K"), ("gu", "13", "Q5_K"),
                 ("dn", "7", "Q5_1"), ("dn", "8", "Q8_0")):
        need(want in combos, "WIDTH_SWEEP.tsv lost the production combination %s" % (want,))
        got = pts.get(want[:2], set())
        need(got == {32, 128, 320, 512, 1024},
             "WIDTH_SWEEP.tsv %s must cover 32/128/320/512/1024, got %s"
             % (want[2], sorted(got)))
    # the whole point of the sweep: gate/up must NOT be repacked, down must be
    gu = [float(l.split("\t")[6]) for l in srows
          if l.startswith("gu\t") and len(l.split("\t")) == 10]
    dn = [float(l.split("\t")[6]) for l in srows
          if l.startswith("dn\t") and len(l.split("\t")) == 10]
    need(gu and min(gu) > 1.5,
         "gate/up repack suddenly pays off (min ratio32 %.3f) — re-read PORT_STATUS.md" % (min(gu) if gu else -1))
    need(dn and max(dn) < 0.90,
         "down repack no longer pays (max ratio32 %.3f) — re-read PORT_STATUS.md" % (max(dn) if dn else -1))

if FAILS:
    print("VERIFY: FAIL (%d)" % len(FAILS))
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("VERIFY: PASS (6 groups: artifacts, results, fair-AB markers, port status, CI wiring, width/type sweep)")
