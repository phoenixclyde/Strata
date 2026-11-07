#!/usr/bin/env python3
# W840-01 机械盘点：未审计轮次 / 登记表完整性 / 文档清单
import io, os, re, glob, collections

D = "D:/workbuddy_space/strata_ws/deploy"

# 1) 所有 W8xx 文档
docs = sorted(glob.glob(D + "/W8*.md"))
print("=== deploy 下 W8xx 文档 ===")
for f in docs:
    print("  %8d  %s" % (os.path.getsize(f), os.path.basename(f)))

# 2) 审计件里已经出现过哪些 W 轮次
aud = sorted(glob.glob(D + "/AUDIT*.md"))
print("\n=== 审计件 ===")
for f in aud:
    print("  %8d  %s" % (os.path.getsize(f), os.path.basename(f)))

text = ""
for f in aud:
    text += io.open(f, encoding="utf-8", errors="replace").read()
for f in glob.glob(D + "/AUDIT_LEDGER.tsv"):
    text += io.open(f, encoding="utf-8", errors="replace").read()

print("\n=== 各轮在审计件中的出现次数（0 = 未审） ===")
missing = []
for n in range(776, 845):
    tag = "W%d" % n
    c = text.count(tag)
    if c == 0:
        missing.append(tag)
    print("  %-6s %d" % (tag, c))
print("\n未审（出现 0 次）:", " ".join(missing))

# 3) 登记表完整性
REG = D + "/params/PARAM_REGISTER.tsv"
rows = [l.split("\t") for l in io.open(REG, encoding="utf-8").read().split("\n") if l.strip()]
print("\n=== 登记表 ===")
print("  行数(含表头) %d，列数应为 %d" % (len(rows), len(rows[0])))
bad = [(r[0], len(r)) for r in rows[1:] if len(r) != 11]
print("  列数异常行:", bad if bad else "无")
ids = [r[0] for r in rows[1:]]
dup = [k for k, v in collections.Counter(ids).items() if v > 1]
print("  重复 ID:", dup if dup else "无")
print("  最后 5 条:", [r[0] for r in rows[-5:]])
st = collections.Counter(r[5] for r in rows[1:] if len(r) > 5)
print("  状态分布:", dict(st))

# 4) 本地改动工作量（本轮相关目录）
for sub in ("albus/w832", "albus/w833", "albus/w834", "albus/w835", "albus/w836", "albus/w837", "albus/w838", "albus/w839"):
    p = "D:/workbuddy_space/strata_ws/" + sub
    if os.path.isdir(p):
        fs = sorted(glob.glob(p + "/*"))
        print("%-12s %2d files, %8d bytes" % (sub.split("/")[-1], len(fs), sum(os.path.getsize(x) for x in fs if os.path.isfile(x))))
