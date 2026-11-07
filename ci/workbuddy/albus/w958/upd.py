# -*- coding: utf-8 -*-
"""W958: retire the token-equality criterion in W956 §9, note in PROGRESS, closure row V-6."""
import io, csv, subprocess

# 1) W956 §9 criterion banner
p = "D:/workbuddy_space/strata_ws/deploy/W956_R90_S3_MMQ_API_PORT.md"
s = io.open(p, encoding="utf-8").read()
anchor = "## 9 下一步：S4 的两道门（还没跑）"
add = (anchor + "\n\n> **【W958 更正 2026-11-04 19:2x】本节的判据①作废。** 同二进制重复跑：**A1 vs A2 只有 7/64 个 token 相同**，\n"
       "> 而 0.8.0 移植版两次跑 **64/64 相同** ⇒ 生产件自己就不复现（源码 `generate.cpp:12706`：专家换入换出落在哪个窗口\n"
       "> 决定它用 CPU 还是 GPU 算，两者舍入不同）。验收改为：**性能六长度档 A/B + 质量对金标的 KL/top-1（先测地板）**，\n"
       "> 见 `W958`。\n")
if "【W958 更正" not in s and anchor in s:
    s = s.replace(anchor, add, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    print("W956 banner ok")

# 2) PROGRESS R90
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
rows = list(csv.reader(io.open(P, encoding="utf-8").read().splitlines(), delimiter="\t"))
for r in rows:
    if len(r) > 8 and r[1] == "R90" and "W958" not in r[8]:
        r[8] += (" **【W958 · 19:2x】确定性对照**：A1/A2（同一 0.4.1 二进制）**只有 7/64 个 token 相同**（前缀 3），"
                 "B1 与 `W957` 的 B **64/64 全同** ⇒ **生产件自身 run 间不复现**（源码 `generate.cpp:12706` 写明："
                 "专家换入换出落在哪个窗口决定 CPU/GPU 舍入）。⇒ **\"逐位/token 相同\"判据作废**（不是 0.8.0 不逐位），"
                 "验收改为：性能六长度档 A/B + 质量对金标 KL/top-1（先测地板）；待查假设：rocBLAS 运行期选解 / 换入序列。")
        print("R90 note ok")
io.open(P, "w", encoding="utf-8", newline="").write("\n".join("\t".join(r) for r in rows) + "\n")

# 3) closure ledger row
G = "D:/workbuddy_space/strata_ws/albus/w954/gen_ledger.py"
t = io.open(G, encoding="utf-8").read()
row = (' ("V-6",   "P1", "W958_DETERMINISM_CONTROL.md",           "A1 vs A2",                            "RESOLVED", "逐位判据作废: A 自身 7/64, B 64/64"),\n')
if "V-6" not in t:
    t = t.replace(' ("V-1",', row + ' ("V-1",', 1)
    io.open(G, "w", encoding="utf-8", newline="").write(t)

PY = "C:/Users/clyde/AppData/Local/Programs/Python/Python313/python.exe"
for cmd in ([PY, G], [PY, "D:/workbuddy_space/strata_ws/tools/audit_closure.py"],
            [PY, "D:/workbuddy_space/strata_ws/tools/progress.py"]):
    print("\n".join(subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()[:3]))
    print("---")
