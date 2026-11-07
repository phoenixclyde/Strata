#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W807 解码侧质量门的分析器：逐条 prompt 比四/五臂的**贪心输出文本**。
   输出：每条 prompt 上各臂与 A 的关系（逐字相同 / 首个分歧位置 / 公共前缀长度 / 长度差）。
   底噪 = A 与 A2（同配置两遍）；若 A||A2 不为 0，则本仪器在该配置上没有分辨力。
"""
import json, os, sys

D = sys.argv[1] if len(sys.argv) > 1 else "albus/w807"
ARMS = sys.argv[2].split(",") if len(sys.argv) > 2 else ["A", "A2", "B", "C", "D"]
REF = "A"


def load(a):
    p = os.path.join(D, "w807_decq_%s.json" % a)
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    return {r["i"]: r for r in d["results"]}


data = {a: load(a) for a in ARMS}
have = [a for a in ARMS if data[a]]
print("臂:", have)
if REF not in data or data[REF] is None:
    raise SystemExit("缺参考臂 A")

n = len(data[REF])
print("\n== 每条 prompt 的生成量（参考臂 A）==")
for i in range(n):
    r = data[REF][i]
    print("  p%-2d ptok=%-4s ctok=%-4s finish=%-6s %.1fs chars=%d" %
          (i, r.get("prompt_tokens"), r.get("completion_tokens"), r.get("finish"), r.get("wall_s", 0), r.get("nchar", 0)))

print("\n== 与 A 的逐字比较（字符级）==")
hdr = "%-3s" % "p"
for a in have:
    if a == REF:
        continue
    hdr += "  %-22s" % ("A||" + a)
print(hdr)
summary = {a: {"same": 0, "diff": 0, "prefix": [], "dtok": []} for a in have if a != REF}
for i in range(n):
    line = "%-3d" % i
    ta = (data[REF][i].get("text") or "")
    for a in have:
        if a == REF:
            continue
        tb = (data[a][i].get("text") or "")
        if ta == tb:
            line += "  %-22s" % "逐字相同"
            summary[a]["same"] += 1
        else:
            k = 0
            m = min(len(ta), len(tb))
            while k < m and ta[k] == tb[k]:
                k += 1
            summary[a]["diff"] += 1
            summary[a]["prefix"].append(k)
            da = data[REF][i].get("completion_tokens") or 0
            db = data[a][i].get("completion_tokens") or 0
            summary[a]["dtok"].append(db - da)
            line += "  %-22s" % ("分歧@%d (len %d/%d)" % (k, len(ta), len(tb)))
    print(line)

print("\n== 汇总 ==")
for a in have:
    if a == REF:
        continue
    s = summary[a]
    tot = s["same"] + s["diff"]
    if s["diff"] == 0:
        print("  A||%-3s  %d/%d 条逐字相同 => **无差异**" % (a, s["same"], tot))
    else:
        print("  A||%-3s  %d/%d 条不同；首个分歧位置 %s（占总长比例 %s）；completion_tokens 差 %s"
              % (a, s["diff"], tot, s["prefix"],
                 ["%.1f%%" % (100.0 * k / max(1, len(data[REF][i].get("text") or ""))) for k, i in
                  zip(s["prefix"], [i for i in range(tot) if (data[REF][i].get("text") or "") != (data[a][i].get("text") or "")])],
                 s["dtok"]))
