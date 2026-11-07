import csv, collections, re

P = "/d/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv".replace("/d/", "D:/")
rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
hdr = rows[0]
body = [r for r in rows[1:] if r and r[0].strip()]
print("cols", len(hdr), "rows", len(body))
print("hdr:", hdr)

idx = {h: i for i, h in enumerate(hdr)}
# 找状态列
stat_col = None
for i, h in enumerate(hdr):
    if any(k in h.lower() for k in ("status", "state", "状态", "结论")):
        stat_col = i
        break
print("status col:", stat_col, hdr[stat_col] if stat_col is not None else None)

cnt = collections.Counter()
for r in body:
    s = r[stat_col].strip().split()[0] if stat_col is not None and r[stat_col].strip() else "?"
    cnt[s] += 1
print("status 分布:", cnt.most_common())

print("\n=== 非终态（OPEN/PENDING/CANDIDATE/DEFERRED/TODO）===")
KEY = re.compile(r"OPEN|PENDING|CANDIDAT|DEFER|TODO|待|未测|未验|计划", re.I)
for r in body:
    s = r[stat_col] if stat_col is not None else ""
    if KEY.search(s):
        print("  %-6s %-12s %s" % (r[0], s[:12], (r[2] if len(r) > 2 else "")[:60]))

print("\n=== 最后 8 条编号 ===")
for r in body[-8:]:
    print("  %-6s %-12s %s" % (r[0], (r[stat_col] if stat_col is not None else "")[:12], (r[2] if len(r) > 2 else "")[:70]))
