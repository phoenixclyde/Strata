#!/bin/bash
set -e
cd /home/albus/strata166/pr/strata-fork
python3 - <<'PY'
import io
p = "ci/cfg_apply.py"
s = io.open(p, encoding="utf-8").read()
old = "            better = dd > band_d or dt2 < -band_t"
new = "            better = better or dd > band_d or dt2 < -band_t"
if old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("patched overwrite")
else:
    print("already patched or pattern missing")
PY
python3 -c "import ast,io;ast.parse(io.open('ci/cfg_apply.py').read());print('syntax ok')"
git add ci/cfg_apply.py
git -c user.name=strata -c user.email=strata@local commit -q -m "cfg_apply: the decode/TTFT test overwrote better, discarding a --lengths gain

pool-workers=10 gained +1.92% at 2K (band 1.00%) and was still judged inconclusive, because
the decode/TTFT assignment ran after the per-length loop and reset better."
git log -1 --format='%h %s' | cut -c1-50
