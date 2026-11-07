#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把生产 args/env 逐条对到 PARAM_REGISTER 的状态。"""
import io, json, re

REG = "D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
CFG = "D:/workbuddy_space/strata_ws/albus/w985/live.json"   # 从 166 抓回的配置副本

rows = [l.split("\t") for l in io.open(REG, encoding="utf-8", errors="replace").read().splitlines()[1:]]
reg = [{"id": r[0], "scope": r[1], "name": r[2], "value": r[3], "status": r[5]} for r in rows if len(r) > 5]

cfg = json.load(open(CFG))
args = cfg["args"]
env = cfg["env"]

def find(tok):
    tok = tok.strip()
    hits = [r for r in reg if r["name"].split("=")[0].strip() == tok or r["name"].startswith(tok + " ")]
    return hits

print("%-28s %-34s %-22s %s" % ("live token", "value", "register", "status"))
print("-" * 110)
live = []
for i, a in enumerate(args):
    if a.startswith("--"):
        val = args[i + 1] if (i + 1 < len(args) and not args[i + 1].startswith("--")) else "(bool)"
        live.append((a, val))
for k, v in env.items():
    live.append((k, v))

unregistered, mismatch = [], []
for name, val in live:
    hits = find(name)
    if not hits:
        unregistered.append((name, val))
        print("%-28s %-34s %-22s %s" % (name, str(val)[:34], "-", "** 未登记 **"))
        continue
    st = ",".join(sorted({h["status"] for h in hits}))
    ids = ",".join(h["id"] for h in hits[:3])
    print("%-28s %-34s %-22s %s" % (name, str(val)[:34], ids, st))
    if any(h["status"] in ("REJECTED", "SUPERSEDED", "N/A") for h in hits):
        mismatch.append((name, val, ids, st))

print()
print("未登记（%d）: %s" % (len(unregistered), ", ".join(n for n, _ in unregistered)))
print("登记为 REJECTED/SUPERSEDED 但仍在生产（%d）:" % len(mismatch))
for m in mismatch:
    print("   ", m[0], "=", m[1], "|", m[2], m[3])
