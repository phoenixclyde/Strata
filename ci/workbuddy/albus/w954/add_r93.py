# -*- coding: utf-8 -*-
"""Add R93 to PROGRESS, refresh the closure ledger md5s, and sync the W832 anchor."""
import io, os, hashlib, csv

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
rows = list(csv.reader(io.open(P, encoding="utf-8").read().splitlines(), delimiter="\t"))
ids = {r[1] for r in rows if len(r) > 1}
if "R93" not in ids:
    row = ["B5本机缺口", "R93",
           "0.8.0 上线后重标 chunk（16384 的倒 U 顶点是在 0.4.1 上测的，升级后路径变了）",
           "W954", "count", "1", "0", "OPEN",
           "**W954 立（2026-11-04 17:3x）**：`W941` 的倒 U（16384 最优、32768 −6.4%、8192 −6.2%）是在 **0.4.1** 的 prefill 路径上测的；"
           "`W953` 已确认我们要从 0.4.1 升到 0.8.0（4 个 minor），prefill/chunk 相关代码在 587 行差异内 ⇒ 升级后必须重标，不能沿用旧顶点。"
           "同时复核 `stream_all_min`（默认 1024）阈值：源码注释写明 chunk ≥ 该阈值时「每个未驻留专家都要流一次，不管是否被路由」，"
           "这是倒 U 的机制之一。判据：六长度档 `0 reused`，两端各掉 >2×CV 才算顶点移动。",
           "W954;W953;W941"]
    rows.append(row)
    io.open(P, "w", encoding="utf-8", newline="").write("\n".join("\t".join(r) for r in rows) + "\n")
    print("R93 added")
else:
    print("R93 already")

# refresh ledger md5 + W832 anchor references
import subprocess
print(subprocess.run(["C:/Users/clyde/AppData/Local/Programs/Python/Python313/python.exe",
                      "D:/workbuddy_space/strata_ws/albus/w954/gen_ledger.py"],
                     capture_output=True, text=True).stdout.strip())

md5 = hashlib.md5(io.open("D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md", "rb").read()).hexdigest()
print("W832 md5", md5)
for p in ["D:/workbuddy_space/strata_ws/deploy/AUDIT24_W900_W951.md",
          "D:/workbuddy_space/strata_ws/albus/w952/reply3.md"]:
    if not os.path.exists(p):
        continue
    s = io.open(p, encoding="utf-8").read()
    s2 = s.replace("9bebc69a", md5[:8])
    if s2 != s:
        io.open(p, "w", encoding="utf-8", newline="").write(s2)
        print("anchor synced:", os.path.basename(p))
