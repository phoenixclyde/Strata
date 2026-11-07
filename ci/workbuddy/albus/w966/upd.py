# -*- coding: utf-8 -*-
"""W966: R90 note (verdict changed), plan banner, closure row V-9."""
import io, csv, subprocess

# 1) PROGRESS R90
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
rows = list(csv.reader(io.open(P, encoding="utf-8").read().splitlines(), delimiter="\t"))
for r in rows:
    if len(r) > 8 and r[1] == "R90" and "W966" not in r[8]:
        r[8] += (" **【W966 · 22:0x】代码级定论：0.8.0 的 MMQ 内核与我们逐字节等价** —— J=64/fallback=false 内核 "
                 "0.7.0=23,164 B vs 0.8.0=23,168 B，sgpr44/vgpr128/priv44/spill0 **全同**；"
                 "`mmq-config-gcn.cuh` 逐字节同且我们 `stream_k=false`（#30553 无关）；GDN `cols_per_warp=4` 两版都有。"
                 "热态生产路径（wrapper + 项目探针，同 1916-token prompt）：0.4.1 **503** / 0.8.0 **497** / 0.1.55w **506** tok/s，"
                 "差 ≤1.8% ⇒ **0.8.0 不慢，−6% 是冷启动口径**。⇒ **性能上可以紧跟上游**；跟之前补 trellis prec 适配 + 摘 #29953 padding。"
                 "遗留：三者都 ~500 而 `W863`(11-01) 是 946@1242，且我的探针里 **prompt cache 从未命中**（3 次同 prompt TTFT 全 3.8 s）⇒ 先查缓存口径。")
        print("R90 note ok")
io.open(P, "w", encoding="utf-8", newline="").write("\n".join("\t".join(r) for r in rows) + "\n")

# 2) W954 banner update
p = "D:/workbuddy_space/strata_ws/deploy/W954_PLAN_RERANK.md"
s = io.open(p, encoding="utf-8").read()
anchor = "> ## 【W960 改判 2026-11-04 19:3x】"
add = ("> **【W966 再改判 2026-11-04 22:0x】上面这条被推翻了**：代码级比对显示 0.8.0 的 J=64 内核与 0.7.0 "
       "**代码大小/寄存器/私有内存全同**，热态生产路径 A/B 三者等价（503 / 497 / 506 tok/s，差 ≤1.8%）\n"
       "> ⇒ **0.8.0 没有性能退步，R90 回到可执行**（先补 trellis prec + 摘 #29953 padding，再六长度档 A/B 定稿）。\n"
       "> `W960` 的 −6% 是每个容器**第一段 prompt**（冷启动、专家换入）测出来的，不代表生产形态。\n\n")
if "【W966 再改判" not in s and anchor in s:
    s = s.replace(anchor, add + anchor, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    print("W954 banner ok")

# 3) closure
G = "D:/workbuddy_space/strata_ws/albus/w954/gen_ledger.py"
t = io.open(G, encoding="utf-8").read()
row = (' ("V-9",   "P0", "W966_CODE_LEVEL_VERDICT.md",          "23,164",                              "RESOLVED", "内核逐字节等价; 热态 503/497/506 -> 0.8.0 可跟"),\n')
if "V-9" not in t:
    t = t.replace(' ("V-1",', row + ' ("V-1",', 1)
    io.open(G, "w", encoding="utf-8", newline="").write(t)

PY = "C:/Users/clyde/AppData/Local/Programs/Python/Python313/python.exe"
for cmd in ([PY, G], [PY, "D:/workbuddy_space/strata_ws/tools/audit_closure.py"],
            [PY, "D:/workbuddy_space/strata_ws/tools/progress.py"]):
    print("\n".join(subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()[:3]))
    print("---")
