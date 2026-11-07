# -*- coding: utf-8 -*-
"""W962: update W961 §6 with the bisect result, PROGRESS note, closure row V-8."""
import io, csv, subprocess

# 1) W961 §6 -> result
p = "D:/workbuddy_space/strata_ws/deploy/W961_LLAMACPP_RELEASES_ANALYSIS.md"
s = io.open(p, encoding="utf-8").read()
old = "## 6 −6% 的归因：正在用版本 bisect 定位"
new = "## 6 −6% 的归因：【已定位】fusion `#29948`（见 `W962`）"
if old in s:
    s = s.replace(old, new, 1)
    marker = "- 若 0.7.0 ≈ 600 tok/s ⇒ **fusion 是凶手**，0.8.0 的 −6% 可以精确归因；\n- 若 0.7.0 ≈ 566 tok/s ⇒ 凶手在 10-19/10-15 之前（GDN `#30087` 或更早）。"
    result = ("**结果（`W962`）**：0.7.0 = **594.11 tok/s**（A 599–604，B 552–577）⇒ C 与 B 差 **5.0%**、C 与 A 差 **1.3%**。\n"
              "**⇒ 凶手是 fusion（`c49edf09`，10-25，283 行）：它拿走 ~5%，其余全部改动合计 ~1%。**")
    s = s.replace(marker, result, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    print("W961 updated")

# 2) PROGRESS
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
rows = list(csv.reader(io.open(P, encoding="utf-8").read().splitlines(), delimiter="\t"))
for r in rows:
    if len(r) > 8 and r[1] == "R90" and "W962" not in r[8]:
        r[8] += (" **【W962 · 20:3x】bisect 完成**：0.7.0(`620d222`，有 prec+`J_best`、无 fusion) = **594.11 tok/s**，"
                 "A(0.4.1) 601.7、B(0.8.0) 565.8 ⇒ **C 与 B 差 5.0%、C 与 A 差 1.3%** ⇒ **−6% 出在 fusion `#29948`**"
                 "（0.8.0 的 mmq.cuh 与它逐字节相同）。⇒ 结论：**0.8.0 与 0.7.0 都不划算，留在 0.4.1**，"
                 "要新基线的东西就按 `W961 §5` 摘单个修复（首推 `#29953` 的越界 padding）。")
        print("R90 note ok")
io.open(P, "w", encoding="utf-8", newline="").write("\n".join("\t".join(r) for r in rows) + "\n")

# 3) closure
G = "D:/workbuddy_space/strata_ws/albus/w954/gen_ledger.py"
t = io.open(G, encoding="utf-8").read()
row = (' ("V-8",   "P1", "W962_BISECT_FUSION.md",                "fusion",                             "RESOLVED", "0.7.0=594 vs B=566 vs A=602 -> fusion #29948 是 -5%"),\n')
if "V-8" not in t:
    t = t.replace(' ("V-1",', row + ' ("V-1",', 1)
    io.open(G, "w", encoding="utf-8", newline="").write(t)

PY = "C:/Users/clyde/AppData/Local/Programs/Python/Python313/python.exe"
for cmd in ([PY, G], [PY, "D:/workbuddy_space/strata_ws/tools/audit_closure.py"],
            [PY, "D:/workbuddy_space/strata_ws/tools/progress.py"]):
    print("\n".join(subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()[:3]))
    print("---")
