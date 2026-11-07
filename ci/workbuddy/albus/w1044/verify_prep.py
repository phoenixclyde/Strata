#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run on 166: verify every W1044 window artifact before the stop."""
import hashlib
import io
import json
import os
import sys

W = "/home/albus/strata166/tmp/w1044"
NEED = ["qq_long.py", "set32k.ids.json", "timing.json", "kl_extract.py",
        "window_w1044.sh", "cfg_new.json", "longctx_needle.py", "judge.py",
        "cfgP_kvg.json", "cfgP_attn.json"]
bad = []
for f in NEED:
    p = os.path.join(W, f)
    if not os.path.isfile(p) or os.path.getsize(p) == 0:
        bad.append(f + " MISSING/EMPTY")
        continue
    print("%-24s %9d B  %s" % (f, os.path.getsize(p),
                               hashlib.md5(open(p, "rb").read()).hexdigest()[:12]))

d = json.load(io.open(os.path.join(W, "set32k.ids.json"), encoding="utf-8"))
print("ids: seg_tokens=%s len=%d segments=%d" %
      (d["seg_tokens"], len(d["segments"][0]["ids"]), len(d["segments"])))
if d["seg_tokens"] != 32768 or len(d["segments"][0]["ids"]) != 32768:
    bad.append("set32k ids length")

for f in ("cfgP_kvg.json", "cfgP_attn.json", "cfg_new.json"):
    c = json.load(io.open(os.path.join(W, f), encoding="utf-8-sig"))
    print("%-24s args=%d kvgrow=%s env=%d exe=%s" %
          (f, len(c["args"]), "--kv-grow" in c["args"], len(c["env"]), c["exe"]))
    if "--kv-grow" not in c["args"]:
        bad.append(f + " lost --kv-grow")
if "STRATA_GFX906_ATTN_DP4A" not in json.load(
        io.open(os.path.join(W, "cfg_new.json"), encoding="utf-8-sig"))["env"]:
    bad.append("cfg_new.json has no DP4A env")

t = io.open(os.path.join(W, "qq_long.py"), encoding="utf-8").read()
lines = [l for l in t.splitlines() if l.startswith("PROMPT_LENS")]
print("PROMPT_LENS:", lines)
if lines != ["PROMPT_LENS = (1000, 8000, 20000, 32768)"]:
    bad.append("qq_long.py PROMPT_LENS not patched")

timing = json.load(io.open(os.path.join(W, "timing.json"), encoding="utf-8"))
print("timing:", {k: (v["delta_pct"], v["band_2cv"]) for k, v in timing.items()})
if len(timing) < 2:
    bad.append("timing.json too small")

print("VERIFY_PREP: %s" % ("PASS" if not bad else "FAIL " + "; ".join(bad)))
sys.exit(1 if bad else 0)
