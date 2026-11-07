# -*- coding: utf-8 -*-
"""Ledger lint: rows whose evidence column is empty/placeholder, or whose ref looks like prose."""
import csv

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
rows = [r for r in csv.reader(open(P, encoding="utf-8"), delimiter="\t") if len(r) >= 9]
bad = []
for r in rows:
    if r[0].startswith("#") or r[0] == "block":
        continue
    note, ref, st = r[8], (r[9] if len(r) > 9 else ""), r[7]
    issues = []
    if len(note.strip()) < 20:
        issues.append("note=%r" % note)
    if len(r) != 10:
        issues.append("ncol=%d" % len(r))
    if len(ref) > 60 and ("**" in ref or "实测" in ref):
        issues.append("ref-is-prose")
    if st in ("DONE", "DONE_NEG") and not any(k in note for k in ("实测", "日志", "跑", "A/B", "字节", "源码", "docker", "镜像", "提交", "git")):
        issues.append("closed-without-evidence-word")
    if issues:
        bad.append((r[0], r[1], st, issues, note[:60]))
print("rows %d | flagged %d" % (len(rows), len(bad)))
for b in bad:
    print("%-10s %-5s %-9s %-45s %s" % (b[0][:10], b[1], b[2], ",".join(b[3])[:45], b[4].replace("\n", " ")))
