# -*- coding: utf-8 -*-
"""R90 S4 first-round note + closure row V-5."""
import io, csv, subprocess

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
rows = list(csv.reader(io.open(P, encoding="utf-8").read().splitlines(), delimiter="\t"))
for r in rows:
    if len(r) > 8 and r[1] == "R90" and "W957" not in r[8]:
        r[8] += (" **【W957 · 18:5x】S4 第一轮**：`--dump-logits` 在 native pack 上恒 0 字节（源码注释已写明），"
                 "改用引擎打印的 `output :` token 序列；首次跑 B 臂 abort（`J_best=412`，0.8.0 把 `ncols_opt` 换成 "
                 "`int J_best`，我们的位置初始化把 max_rows 塞进去）→ 加 `pick_J()` 12 行（上游 helper 是 static 调不到）"
                 "修复后两臂 RC=0、各 64 token；**相同前缀 7**（第 8 个 A=33413 / B=1666）。"
                 "这不构成\"0.8.0 不行\"的证据 —— 下一轮先做**同二进制重复跑**的对照（`W899 §7.11` 记过引擎 run 间可能不确定），"
                 "再按 §5 的 4 步定位分叉段；判据也从\"逐位\"改为\"KL≤0.005 且 top-1≥99% 或 64 token 前缀 ≥48\"（`W957 §6`）。")
        print("R90 note ok")
io.open(P, "w", encoding="utf-8", newline="").write("\n".join("\t".join(r) for r in rows) + "\n")

G = "D:/workbuddy_space/strata_ws/albus/w954/gen_ledger.py"
s = io.open(G, encoding="utf-8").read()
add = (' ("V-5",   "P1", "W957_R90_S4_NOT_BITEXACT.md",         "前缀 7",                              "RESOLVED", "0.8.0 端到端可跑; 与 0.4.1 前缀 7/64, 待同二进制对照"),\n')
if "V-5" not in s:
    s = s.replace(' ("V-1",', add + ' ("V-1",', 1)
    io.open(G, "w", encoding="utf-8", newline="").write(s)

PY = "C:/Users/clyde/AppData/Local/Programs/Python/Python313/python.exe"
for cmd in ([PY, G], [PY, "D:/workbuddy_space/strata_ws/tools/audit_closure.py"],
            [PY, "D:/workbuddy_space/strata_ws/tools/progress.py"]):
    print("\n".join(subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()[:3]))
    print("---")
