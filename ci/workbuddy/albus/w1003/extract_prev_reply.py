#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 transcript jsonl 里抽出「上一条助手回复」的正文，落成 md，供 report_lint 复检。

jsonl 结构：{type: "message", role: "assistant", content: [{type:"output_text", text: ...}]}
"""
import json
import sys

src = r"C:\Users\clyde\.workbuddy\projects\d-workbuddy_space-strata_ws\e6f63f19-7bad-4cce-b8ae-46341a66dc8b.jsonl"
out = r"D:\workbuddy_space\strata_ws\albus\w1003\reply_prev.md"

msgs = []
with open(src, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") != "message" or o.get("role") != "assistant":
            continue
        c = o.get("content") or []
        texts = []
        if isinstance(c, str):
            texts.append(c)
        else:
            for p in c:
                if isinstance(p, dict) and p.get("type") in ("output_text", "text"):
                    texts.append(p.get("text") or "")
                elif isinstance(p, str):
                    texts.append(p)
        t = "\n".join(x for x in texts if x.strip())
        if not t.strip():
            continue
        msgs.append((o.get("id", ""), o.get("timestamp", 0), t))

print("assistant text messages:", len(msgs))
# 取最后一条「四件套」形态的长回复（含「四件套」或长度 > 1500）
longs = [m for m in msgs if "四件套" in m[2] or len(m[2]) > 1500]
print("long candidates:", len(longs))
pick = longs[-1] if longs else msgs[-1]
print("pick id=%s len=%d" % (pick[0], len(pick[2])))
open(out, "w", encoding="utf-8").write(pick[2])
print("wrote", out)
