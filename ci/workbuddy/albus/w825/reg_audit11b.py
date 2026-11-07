# -*- coding: utf-8 -*-
"""AUDIT11 收尾：修正 P167 计数、给 P168 补上游证据、新增 P176 测量协议。"""
import csv, os

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "params", "PARAM_REGISTER.tsv"))
rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
hdr, body = rows[0], [r for r in rows[1:] if r and r[0].strip()]
ids = [r[0] for r in body]

changed = []
for r in body:
    if r[0] == "P167":
        r[10] = r[10].replace("P0=3 / P1=12 / P2=9", "P0=3 / P1=12 / P2=8")
        changed.append("P167 计数→P2=8")
    if r[0] == "P168":
        r[9] = r[9] + ("  **上游同款证据**：`tools/calibrate.py` 里 `def warm_up(self, rounds: int = 2)` 默认预热 2 轮，"
                       "`SWEEP_ROUNDS = 3` 每值扫 3 轮且顺序交替，判据 `min(gains) > 0.0 and median(gains) > MIN_GAIN(0.03)` "
                       "⇒ 「每轮都赢 + 中位超阈值」。**我们的自制脚本一件都没做**。")
        changed.append("P168 补上游证据")

NEW = [
    ["P176", "measurement", "A/B 测量协议（warm_up 2 + 3 轮交替 + 每轮都赢）", "见 evidence",
     "measurement", "ADOPTED", "—", "—", "P168/P169",
     "①`mt_read.py` 已加第 8 个参数 `WARM`（默认 2），预热用另一段文本（`take()` 推进 `cur`）以免正式测量命中 prompt 缓存，"
     "预热墙钟写入输出 JSON 的 `warm_wall`；已实测：`warm0 3.63s → warm1 3.28s → rep0 3.34s`。"
     "②判据对齐上游 `calibrate.py`：`SWEEP_ROUNDS=3`、顺序交替（ABBA）、`min(gains)>0.0 and median(gains)>0.03`。",
     "**这条能同时消掉三个历史假象**：①427 vs 525 的基线差；②短档方差 4.6% 与长档 0.1% 的差；"
     "③W810 前两档各多 265/398 ms。**执行要求**：任何 A/B 臂的新容器，第一个测量请求之前必须跑满 2 轮预热；"
     "旧数据（W804/W810/W822/W824）的读数都带这个偏差，引用时要标注。"],

    ["P177", "measurement", "上游 calibrate 自带预热，故 P0 优先级再升", "—",
     "measurement", "CONFIRMED", "—", "—", "P160/P176",
     "`tools/calibrate.py:219` 的 `warm_up(rounds=2)`、`:52` 的 `SWEEP_ROUNDS=3`、`:180` 的判据 —— 三者构成一套完整协议，"
     "而我们的自制脚本没有一项。跑它一次 = 同时把「参数标定」与「测量协议」两件事对齐上游。",
     "P0 从「推荐第一件事」升为「**必须先做**」：它不只是拿 5 个参数的最优值，"
     "还是我们唯一一次能在上游标准协议下重测基线的机会。"],
]

added = []
for r in NEW:
    if r[0] in ids:
        print("skip", r[0]); continue
    body.append(r); added.append(r[0])

with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(hdr); w.writerows(body)

print("changed:", changed)
print("added:", added)
print("rows:", len(body), "cols_ok:", all(len(r) == 11 for r in body))
