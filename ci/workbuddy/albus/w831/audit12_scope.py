# -*- coding: utf-8 -*-
"""AUDIT12 范围判定：哪些轮次已有文档、哪些已被任一审计件在正文里审过、差集是什么。

与 AUDIT11 的 audit_scope.py 的区别：这里用**全文**复核（不是只扫前 40 行），
避免"AUDIT11 只在正文深处提到 W826"这类误判。
"""
import os, re, glob, collections

DEP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "deploy"))
files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(DEP, "*.md")))

round_docs = collections.defaultdict(list)
for f in files:
    for m in re.finditer(r"W(\d{3})", f):
        round_docs[int(m.group(1))].append(f)

AUDIT_PAT = re.compile(r"AUDIT|REVIEW|VERDICT", re.I)
audits = [f for f in files if AUDIT_PAT.search(f) and not f.startswith("W")]

print("=== 审计文档 %d 份 ===" % len(audits))
for a in audits:
    print("   ", a)

# 全文覆盖：审计文档正文里出现过的轮次编号
covered = collections.Counter()
for a in audits:
    txt = open(os.path.join(DEP, a), encoding="utf-8", errors="replace").read()
    for x in {int(v) for v in re.findall(r"W(\d{3})", txt)}:
        covered[x] += 1

all_rounds = sorted(round_docs)
print("\n=== 全部轮次 %d 个：%d..%d ===" % (len(all_rounds), all_rounds[0], all_rounds[-1]))

gap = [r for r in all_rounds if covered.get(r, 0) == 0]
print("\n=== 全文从未被任何审计件提及的轮次（%d 个）===" % len(gap))
for r in gap:
    print("   W%-4d  %s" % (r, ", ".join(round_docs[r][:3])))

# 只被"非审计"文档提及 = 不算审过；单独列出 W800 以后的覆盖情况
print("\n=== W800 以后各轮的『被审计件提及次数』===")
for r in [x for x in all_rounds if x >= 800]:
    docs = ", ".join(sorted(set(round_docs[r])))
    print("   W%-4d 提及=%d  %s" % (r, covered.get(r, 0), docs[:90]))
