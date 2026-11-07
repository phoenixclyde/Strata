"""扫全库找出"已识别但可能没入账"的待办/候选/未测条目。

用法: python tools/ledger_scan.py [--all]
输出: albus/w843/scan_raw.tsv  + 控制台按文件计数
"""
import glob
import io
import os
import re

ROOT = "D:/workbuddy_space/strata_ws"
KW = re.compile(r"(待办|下一步|未测|待测|候选|CANDIDATE|PENDING|UNRESOLVED|建议|值得一试|可试|尚未|没测|未验证|TODO)")
SKIP = re.compile(r"(\.bak|_bak|MEMORY_DETAIL|STATUS_|PROGRESS|W842_SIMT2)")

files = []
files += [p for p in glob.glob(ROOT + "/deploy/*.md") if not SKIP.search(p)]
files += glob.glob(ROOT + "/albus/*/mem_*.md")
files += glob.glob(ROOT + "/albus/*/sec*.md")
files += [p for p in glob.glob(ROOT + "/*.md")]

rows = []
for p in sorted(set(files)):
    try:
        txt = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        continue
    for i, ln in enumerate(txt, 1):
        s = ln.strip()
        if len(s) < 12 or not KW.search(s):
            continue
        if s.startswith("|") and s.count("|") > 3:      # 表格行也收，但合并空白
            s = re.sub(r"\s*\|\s*", " | ", s)
        rows.append((os.path.relpath(p, ROOT).replace("\\", "/"), i, s[:300]))

out = ROOT + "/albus/w843/scan_raw.tsv"
os.makedirs(os.path.dirname(out), exist_ok=True)
with io.open(out, "w", encoding="utf-8", newline="\n") as f:
    f.write("file\tline\ttext\n")
    for r in rows:
        f.write("%s\t%d\t%s\n" % r)

from collections import Counter
c = Counter(r[0] for r in rows)
print("命中 %d 行，来自 %d 个文件 -> %s" % (len(rows), len(c), out))
for k, v in c.most_common(30):
    print("  %4d  %s" % (v, k))
