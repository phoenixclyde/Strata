# -*- coding: utf-8 -*-
"""登记 W832 的 P209/P210，并更新 AUDIT_INDEX 的未结清清单。"""
import io

REG = "D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
IDX = "D:/workbuddy_space/strata_ws/deploy/AUDIT_INDEX.md"

s = io.open(REG, encoding="utf-8").read()
rows = [
 ("P209", "PROCESS", "调优方案按 AUDIT12 重排（W832 V2）：下架 4 条、新增 5 项队列",
  "W832_OPT_PLAN_V2.md 取代 W829 的执行顺序", "process", "ADOPTED",
  "—", "—", "P203/P204/P208",
  "下架：`--batch 2/4`（KV 账差 14 倍）、`--batch 9..16`（装不下）、\"五项结清=最优点\"（效应<噪声）、"
  "`--spec 8 为空操作`（判据列混用）。新增队列：P0-a 参数同实例重判、P0-b 0.1.53 vs n2 同源 A/B、"
  "P0-c 数值债剩余 3 项、P1-a gfx1151 剩余 12 项 mega-arm、P1-b pool-workers ABBA。",
  "采纳。每轮须先写判据与停机条件。"),

 ("P210", "MEASUREMENT", "`--spec-min-p` / `--pcie-frac` 同实例重判：邻居全不优，但效应小于噪声 ⇒ 不可判",
  "保留生产值 0.70 / 0.20；标 UNRESOLVED 而非\"最优\"", "measurement", "UNRESOLVED",
  "—", "—", "P208/P209",
  "方法：单次启动 + `STRATA_DECODE_TIMING=1` + `strata_tune` 逐请求下发 + 6 组随机区组 + 声明判据 tokens/win÷ms/win，"
  "36 条 512-token。结果（配对中位）：spec 0.50 −1.4%(5/6 负)、0.85 +0.0%(3/6)；pcie 0.10 −1.5%(4/6)、0.30 −4.4%(4/6)。"
  "**噪声底盘 3.9–10.8%（中位 6.0%）** ⇒ 效应全在噪声内。噪声来源实测：同一 prompt/seed/temperature=0 的 33 条 512-token "
  "生成给出 33 个不同 sha（含两次同参数）⇒ 生成路径不可复现 ⇒ 不同 token 序列 ⇒ 接受率不同。"
  "⇒ 旧数字 `0.50 只高 0.4%`、`0.20 全局最优` 均小于噪声，作废。压低噪声只有两条：n≥20，或改用与内容无关的量。",
  "关账：保留现值，不再花窗口重测这两项。"),
]
for r in rows:
    if ("\n" + r[0] + "\t") in ("\n" + s):
        print(r[0], "exists")
    else:
        s += "\t".join(r) + "\n"
        print(r[0], "added")
io.open(REG, "w", encoding="utf-8", newline="\n").write(s)
print("register rows:", len([l for l in s.split("\n") if l.strip()]))

# --- 更新索引里的\"未结清\" ---
t = io.open(IDX, encoding="utf-8").read()
old = "| `--spec-min-p` / `--pool-workers` 的效应（0.4%/0.7%）低于自述 12–16% 漂移 | W829 §5.2、AUDIT12 §8-1 | **未判**，不应写作\"最优\" |"
new = ("| ~~`--spec-min-p`~~ / `--pcie-frac` | W832 §4.1（P210） | **已关账**：效应 ≤4.4% < 噪声 6.0%，保留现值，标 UNRESOLVED |\n"
       "| `--pool-workers` 的效应（0.7%）低于噪声 | W829 §5.2、AUDIT12 §8-1 | **仍未判**（需 ABBA，约 20 min） |")
if old in t:
    io.open(IDX, "w", encoding="utf-8", newline="\n").write(t.replace(old, new, 1))
    print("index updated")
else:
    print("index anchor MISSING")
