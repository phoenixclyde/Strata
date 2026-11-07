# -*- coding: utf-8 -*-
"""W960: demote R90 in the plan, promote R88; PROGRESS note; closure row V-7."""
import io, csv, subprocess

# 1) W954 banner + table note
p = "D:/workbuddy_space/strata_ws/deploy/W954_PLAN_RERANK.md"
s = io.open(p, encoding="utf-8").read()
anchor = "---\n\n## 1 排序规则"
banner = """---

> ## 【W960 改判 2026-11-04 19:3x】**R90 从第一位降为"参考实现 / 按需摘取"，R88 回到第一位**
>
> 理由（实测，`W960`）：0.8.0 的移植版 prefill **602 → 566 tok/s（−6.0%，3 vs 3，区间不重叠，t≈4.9）**，
> decode 持平；而 `mmq-config-gcn.cuh` 与 0.4.1 逐字节相同（`W955`）⇒ **4 个 minor 没有带来收益，只带来 −6%**。
> "J 选错"与"精度参数选错"两项已排除（`pick_J` 与 0.4.1 同解，均为 J=64；上游自己的规则也是 `GGML_PREC_Q8`）。
>
> 新排序：**R88（异步分阶段拷贝）→ R86-A/B → R87 → R46 → R91 → R93（改挂到 0.4.1 的 chunk 重标）**；
> `R90` 只保留两件事：**摘**具体修复（逐条 A/B）、以及作为对照树存在，**不做整树上线**。
>
> 唯一未排除的混淆项是 overlay=ON/OFF（`W956 §5.1` 的 trellis ctor 未适配）——先补它再复测，才能 100% 归因。

"""
if "【W960 改判" not in s and anchor in s:
    s = s.replace(anchor, banner + anchor, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    print("W954 banner ok")

# 2) PROGRESS
P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
rows = list(csv.reader(io.open(P, encoding="utf-8").read().splitlines(), delimiter="\t"))
for r in rows:
    if len(r) > 8 and r[1] == "R90" and "W960" not in r[8]:
        r[8] += (" **【W960 · 19:3x】性能实测**：A(0.4.1) 601.74/604.28/599.17、B(0.8.0) 568.41/552.15/576.82 "
                 "⇒ **prefill −6.0%**（区间不重叠，Welch t≈4.9），decode 持平 19.0；`pick_J` 实测两类型 J=64 与 0.4.1 同解、"
                 "上游规则也是 GGML_PREC_Q8 ⇒ 排除我们选错。**R90 降级为参考实现/按需摘取，不做整树上线**；"
                 "队列第一回到 R88。唯一未排除混淆项 = overlay ON/OFF（trellis ctor 未适配）。")
        print("R90 note ok")
io.open(P, "w", encoding="utf-8", newline="").write("\n".join("\t".join(r) for r in rows) + "\n")

# 3) closure
G = "D:/workbuddy_space/strata_ws/albus/w954/gen_ledger.py"
t = io.open(G, encoding="utf-8").read()
row = (' ("V-7",   "P0", "W960_R90_PERF_REGRESSION.md",          "prefill −6.0%",                       "RESOLVED", "0.8.0 prefill 慢 6%(3v3); R90 降级, R88 上位"),\n')
if "V-7" not in t:
    t = t.replace(' ("V-1",', row + ' ("V-1",', 1)
    io.open(G, "w", encoding="utf-8", newline="").write(t)

PY = "C:/Users/clyde/AppData/Local/Programs/Python/Python313/python.exe"
for cmd in ([PY, G], [PY, "D:/workbuddy_space/strata_ws/tools/audit_closure.py"],
            [PY, "D:/workbuddy_space/strata_ws/tools/progress.py"]):
    print("\n".join(subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()[:3]))
    print("---")
