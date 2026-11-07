# -*- coding: utf-8 -*-
"""对候选缺口做全文复核：这些编号是否在任何审计文档正文里被当作审计对象讨论。"""
import os, re, glob

DEP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "deploy"))
files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(DEP, "*.md")))
AUDIT_PAT = re.compile(r"AUDIT|REVIEW|VERDICT", re.I)
audits = [f for f in files if AUDIT_PAT.search(f)]

CAND = [718, 724, 727, 741, 810, 815, 816, 820, 822, 823, 824, 825]

for r in CAND:
    tag = "W%d" % r
    hits = []
    for a in audits:
        txt = open(os.path.join(DEP, a), encoding="utf-8", errors="replace").read()
        n = len(re.findall(re.escape(tag), txt))
        if n:
            hits.append((a, n))
    print("=== %s : %d 份审计文档提到，共 %d 次" % (tag, len(hits), sum(h[1] for h in hits)))
    for a, n in hits:
        print("     %-40s x%d" % (a, n))
    if not hits:
        print("     （任何审计文档均未提及）")
