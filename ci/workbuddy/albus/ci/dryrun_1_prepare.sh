#!/bin/bash
# [W863] Step 1 of a full dry run: record the R28 finding in the source, then run the static gate.
#
# R28 said "the HC down kernel reads Q8_0 weights with 2-byte loads; widen to uint4".
# The arithmetic kills it: a Q8_0 block is 34 bytes (2 d + 32 q), so a block's address is
# 0 or 2 mod 4 -> a 32-bit load of q is misaligned half the time (UB on GCN).  The note goes
# next to the layout constants so the next person does not re-derive it.
#
# The change is a comment only: behaviour is identical, which makes it a good control for
# the L3 gate (a zero-change binary must be judged NOISE, not REAL).
set -u
R=/home/albus/strata166/pr/strata-fork
F=$R/src/kernels/cuda/fused_gr.cu
CI=/home/albus/strata166/ci

cd "$R" || exit 1
echo "=== backup ==="
cp -f "$F" "$F.w863r28bak"
ls -l "$F" "$F.w863r28bak"

echo "=== insert the note (idempotent) ==="
python3 - "$F" <<'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
mark = "W863/R28:"
anchor = "constexpr int Q8B = 34;"
note = (
    "// W863/R28: a Q8_0 block is 34 bytes (2 d + 32 q), so a block address is 0 or 2 mod 4 and a\n"
    "// 32-bit load of q would be misaligned half the time (UB on GCN).  Reading q as two 16-bit\n"
    "// halves keeps it legal; widening the load needs a 36-byte padded layout, i.e. a pack-format\n"
    "// change, not a kernel tweak.  Measured: 176 blocks / 60 CU is not the limit either (block\n"
    "// count is inverse to rows-per-block, and fewer blocks was faster: 69.3 -> 59.5 us).\n"
)
if mark in s:
    print("already noted")
    raise SystemExit(0)
if s.count(anchor) != 1:
    print("ABORT: anchor found %d times" % s.count(anchor)); raise SystemExit(2)
s = s.replace(anchor, note + anchor, 1)
open(p, "w", encoding="utf-8").write(s)
print("note inserted before", anchor)
PY

echo
echo "=== files changed ==="
git status --porcelain --untracked-files=no
echo
echo "=== L1 static gate (this must pass before anything else) ==="
"$CI/strata-ci" check
echo "GATE_RC=$?"
