# -*- coding: utf-8 -*-
"""W928b: 修正队列行（M3 提级、R74 上限改 3.22%）"""
import io

p = "W832_OPT_PLAN_V2.md"
s = io.open(p, encoding="utf-8").read()
lines = s.split("\n")
for i, l in enumerate(lines):
    if l.startswith("> **执行顺序（2026-11-04"):
        lines[i] = (
            "> **执行顺序（2026-11-04 00:5x 修，`W928`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ "
            "→ ~~R61~~ → ~~R60~~ → ~~R58~~ → ~~R63~~ → ~~R64~~ → ~~R73~~ → **M3（k8v8=`--kv int8` 的 prefill "
            "代价，零代码只换参数）** → **R74（W4A4 精度门；上限已修正为 prefill 4.41%/端到端 3.22%，"
            "恰在噪声门上）** → R69 → R70 → R65 → R49 → R50 → R30′**"
        )
        print("queue fixed")
        break
io.open(p, "w", encoding="utf-8").write("\n".join(lines))
