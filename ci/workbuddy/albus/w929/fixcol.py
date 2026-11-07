# -*- coding: utf-8 -*-
"""修正 P258 列数：11 列（id/scope/name/value/family/status/requires/conflicts/synergizes/evidence/verdict）"""
import io

q = "params/PARAM_REGISTER.tsv"
lines = io.open(q, encoding="utf-8").read().split("\n")
for i, l in enumerate(lines):
    f = l.split("\t")
    if f and f[0] == "P258" and len(f) == 10:
        # 当前: id, REF, name, value, kv, REFERENCE, P04, -, "P50;P247", verdict
        # 目标: 插入一个 "-" 到 conflicts_with 位置（第 8 列后）
        fixed = f[:8] + ["-"] + f[8:]
        lines[i] = "\t".join(fixed)
        print("P258 fixed -> NF=", len(fixed))
        print("  cols:", [x[:28] for x in fixed])
        break
io.open(q, "w", encoding="utf-8").write("\n".join(lines))
