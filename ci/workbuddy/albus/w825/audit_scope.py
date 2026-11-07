# -*- coding: utf-8 -*-
"""算清：哪些轮次有文档、哪些被审计文档显式点名审计过、差集是什么。"""
import os, re, glob, collections

DEP = os.path.join(os.path.dirname(__file__), "..", "..", "deploy")
DEP = os.path.abspath(DEP)

files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(DEP, "*.md")))

# 1) 全部轮次编号（从文档名）
round_docs = collections.defaultdict(list)
for f in files:
    for m in re.finditer(r"W(\d{3})", f):
        round_docs[int(m.group(1))].append(f)

# 2) 审计文档（名字里带 AUDIT / REVIEW / VERDICT 且是审计性质的）
AUDIT_PAT = re.compile(r"AUDIT|REVIEW|VERDICT", re.I)
audits = [f for f in files if AUDIT_PAT.search(f)]
print("=== 审计文档 %d 份 ===" % len(audits))
for a in audits:
    print("   ", a)

# 3) 每份审计文档正文里被"点名审计"的轮次（取前 40 行 = 范围声明区）
print("\n=== 各审计文档声明的范围（前 40 行里出现的 W 编号）===")
declared = {}
for a in audits:
    txt = open(os.path.join(DEP, a), encoding="utf-8", errors="replace").read().splitlines()[:40]
    head = "\n".join(txt)
    ws = sorted({int(x) for x in re.findall(r"W(\d{3})", head)})
    declared[a] = ws
    rng = "%d-%d" % (min(ws), max(ws)) if ws else "-"
    print("   %-38s W%s (n=%d)" % (a, rng, len(ws)))

# 4) 被任一审计文档在"范围区"点名的轮次
covered = set()
for a, ws in declared.items():
    covered.update(ws)

# 补充：AUDIT6 明说 "W775delta 及以前（含 AUDIT5） 是"
all_rounds = sorted(round_docs)
print("\n=== 全部轮次（按编号）===")
print("   ", all_rounds)

print("\n=== 未被任何审计文档的『范围区』点名的轮次 ===")
gap = [r for r in all_rounds if r not in covered]
for r in gap:
    print("   W%-4d  文档: %s" % (r, ", ".join(round_docs[r][:3])))

# 5) 反向：审计文档范围区提到但无独立文档的（说明并入别的文档）
print("\n=== 审计范围提到、但无独立文档名的编号（应为并入型）===")
for r in sorted(covered):
    if r not in round_docs:
        print("   W%d" % r)
