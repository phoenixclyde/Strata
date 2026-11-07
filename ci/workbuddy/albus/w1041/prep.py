#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1041 / R103 重开：stage the four numeric arms on 166 (nothing starts yet).

  tmp/w1041/qq_r103.py   = the R104 yardstick: PROMPT_LENS widened to four lengths + a QQ_KV override
  tmp/w1041/set20k.ids.json = the same 20000-token segment used by R104
  cfgA = b12180, k8v4 (baseline)
  cfgB = pa5,   k8v4, no switch        (build floor: MUST be byte-identical to A)
  cfgC = pa5,   k8v4, + ATTN_DP4A=1    (the -11.3% attn arm)
  cfgD = b12180, KV f16               (the anchor: what k8v4 itself already costs)
"""
import io, json, os, sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

S = r'''
set -e
S=/home/albus/strata166
W=$S/tmp/w1041
mkdir -p $W
cp -f $S/tmp/w1041/qq_k8v4.py $W/qq_r103.py
cp -f $S/tmp/w1040/set20k.ids.json $W/set20k.ids.json
python3 - <<'PY'
import io
p = "/home/albus/strata166/tmp/w1041/qq_r103.py"
s = io.open(p, encoding="utf-8").read()
old = "PROMPT_LENS = (256, 512, 768, 1000)"
if old in s:
    s = s.replace(old, "PROMPT_LENS = (1000, 8000, 16000, 20000)")
anchor = "    fixed = list(FIXED)\n"
assert anchor in s, "anchor missing"
ins = ("    fixed = list(FIXED)\n"
       "    _kv = os.environ.get(\"QQ_KV\")\n"
       "    if _kv:\n"
       "        fixed[fixed.index(\"--kv\") + 1] = _kv\n")
s = s.replace(anchor, ins, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("patched:", "PROMPT_LENS" in s, "QQ_KV" in s)
PY
python3 - <<'PY'
import io, json
cfg = json.load(io.open("/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json", encoding="utf-8-sig"))
def mk(path, exe, tag):
    d = json.loads(json.dumps(cfg))
    d["exe"] = exe
    a = [x for x in d["args"] if x != "--kv-grow"]          # irrelevant to the attn question; keep arms comparable
    for i, x in enumerate(a):
        if x == "--expert-profile-save" and i + 1 < len(a):
            a[i + 1] = "/w/qq-profile11-%s.bin" % tag
    d["args"] = a
    json.dump(d, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(path, exe, "args=", len(a), "kv-grow:", "--kv-grow" in a)
mk("/home/albus/strata166/tmp/w1041/cfgA.json", "/data/bin/strata-0.1.57-b12180", "a")
mk("/home/albus/strata166/tmp/w1041/cfgB.json", "/data/bin/strata-0.1.57-pa5", "b")
mk("/home/albus/strata166/tmp/w1041/cfgC.json", "/data/bin/strata-0.1.57-pa5", "c")
mk("/home/albus/strata166/tmp/w1041/cfgD.json", "/data/bin/strata-0.1.57-b12180", "d")
PY
md5sum $W/qq_r103.py $W/cfgA.json $W/cfgB.json $W/cfgC.json $W/cfgD.json
'''
rc, out, err = _sshutil.run_remote(S, timeout=180)
print("rc=", rc)
print(out[-1200:])
if err.strip():
    print("STDERR:", err[-800:])
