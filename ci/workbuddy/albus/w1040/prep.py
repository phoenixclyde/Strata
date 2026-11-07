#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1040: stage the numeric arms on 166 (zero downtime, nothing starts yet).

  tmp/w1040/qq_prompt.py    = the yardstick, PROMPT_LENS widened to (1000, 8000, 16000, 20000)
  tmp/w1040/set20k.ids.json = one 20000-token segment built from the committed 5x1000 set
  tmp/w1040/cfg_armA.json   = production config, --expert-profile-save redirected (b12180)
  tmp/w1040/cfg_armB.json   = same + exe=kvg + --kv-grow
  tmp/w1040/cfg_new.json    = the exact bytes to install (md5 ee69ebc2...)
"""
import io, json, os, sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

W = r"D:/workbuddy_space/strata_ws/albus/w1040"
S = r'''
set -e
S=/home/albus/strata166
W=$S/tmp/w1040
mkdir -p $W
cp -f $S/tmp/w1041/qq_k8v4.py $W/qq_prompt.py
python3 - <<'PY'
import io
p = "/home/albus/strata166/tmp/w1040/qq_prompt.py"
s = io.open(p, encoding="utf-8").read()
old = "PROMPT_LENS = (256, 512, 768, 1000)"
assert old in s, "anchor missing"
s = s.replace(old, "PROMPT_LENS = (1000, 8000, 16000, 20000)")
io.open(p, "w", encoding="utf-8").write(s)
print("patched PROMPT_LENS")
PY
python3 - <<'PY'
import io, json
src = "/home/albus/strata166/pr/k10/data/quant_quality/v1/set.ids.json"
d = json.load(io.open(src))
long = []
for _ in range(4):
    for s in d["segments"]:
        long += s["ids"]
long = long[:20000]
out = {"version": "w1040-long", "seg_tokens": 20000, "vocab_size": d.get("vocab_size"),
       "segments": [{"name": "long", "ids": long}]}
io.open("/home/albus/strata166/tmp/w1040/set20k.ids.json", "w").write(json.dumps(out))
print("ids", len(long), "max id", max(long))
PY
python3 - <<'PY'
import io, json
cfg = json.load(io.open("/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json", encoding="utf-8-sig"))
def mk(path, exe, grow, tag):
    d = json.loads(json.dumps(cfg))
    d["exe"] = exe
    a = d["args"]
    for i, x in enumerate(a):
        if x == "--expert-profile-save" and i + 1 < len(a):
            a[i + 1] = "/w/qq-profile10-%s.bin" % tag
    if grow:
        assert "--kv-grow" not in a
        a.append("--kv-grow")
    json.dump(d, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(path, exe, "grow=", grow, "args=", len(a))
mk("/home/albus/strata166/tmp/w1040/cfg_armA.json", "/data/bin/strata-0.1.57-b12180", False, "a")
mk("/home/albus/strata166/tmp/w1040/cfg_armB.json", "/data/bin/strata-0.1.57-kvg", True, "b")
PY
md5sum $W/cfg_armA.json $W/cfg_armB.json $W/qq_prompt.py
'''
rc, out, err = _sshutil.run_remote(S, timeout=180)
print("rc=", rc)
print(out)
if err.strip():
    print("STDERR:", err[-1500:])

ok, size, md5, det = _sshutil.push_b64(os.path.join(W, "cfg_new.json"),
                                      "/home/albus/strata166/tmp/w1040/cfg_new.json")
print("push cfg_new:", ok, size, md5, det)
rc, out, err = _sshutil.run_remote(
    "md5sum /home/albus/strata166/tmp/w1040/cfg_new.json; ls -1 /home/albus/strata166/tmp/w1040", timeout=60)
print(out)
