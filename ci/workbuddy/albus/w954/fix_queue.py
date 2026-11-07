# -*- coding: utf-8 -*-
"""W954: rewrite the execution order (evidence-weighted) and add R93 to the plan table."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()

old = s[s.find("> **执行顺序（2026-11-04 16:3x 修"):]
old = old[:old.find("\n")]
new = ("> **执行顺序（2026-11-04 17:3x 重排 · `W953`/`W954`；规则：先按停服次数分档，档内按「期望端到端 × 证据系数」，"
       "带精度门的往后一档）：**\n"
       "> **零停服档**：**R90-S1**（pin→tag 映射已完成，下 0.8.0 全目录）→ **R90-S2**（关 `STRATA_MMQ_TAB` 先编通，新 build 目录）"
       "→ **R88-量**（读 0.8.0 调度器 + 从日志量 wait-copy 绝对 ms）→ **R90-S3**（重做 mirror + 逐位测试）\n"
       "> **一次停服档（bit-exact 优先）**：**R86-A/B**（Q5_1 repack 单内核，Δ≥40% 才动生产）→ **R87**（q8_1 复用，先量）\n"
       "> **一次停服档（改行为）**：**R90-S4**（0.8.0 上线六长度档 A/B；回滚 = `STRATA_GGML_DIR` 指回旧树）"
       "→ **R88-实现**（异步分阶段拷贝，照 furnace）→ **R46**（attn 效率，先拆三段）\n"
       "> **精度门档**：**R91-P1/P3**（零停服）→ **R91-P4**（KL 门，不过即停）\n"
       "> **验收/尾部**：**R93**（0.8.0 上线后重标 chunk）→ R72 → R81 → R79 → R80 → R63/R60/R64（只作实跑验证）→ R49 → R50 → R30′\n"
       "> **R84 已并入 R91 的 P0**（同一件事，避免双记）；**R85 只作验收口径**（801→≥850），不占队列位置。")
if "> **执行顺序（2026-11-04 17:3x 重排" not in s:
    s = s.replace(old, new, 1)

row93 = ("| **新28** | **R93** | **0.8.0 上线后重标 chunk**：16384 的倒 U 顶点是在 **0.4.1** 上测的（`W941`），"
         "升级后 prefill 路径变了，顶点可能移动；同时复核 `stream_all_min`（1024）阈值的行为 | "
         "六个长度档 `0 reused`；顶点的两端各掉 >2×CV 才算移动 | `|Δ| ≥ 2×CV`，写清 chunk/长度/T |\n")
anchor = None
for ln in s.split("\n"):
    if ln.startswith("| **新27** | **R91**"):
        anchor = ln
        break
if anchor and "新28" not in s:
    s = s.replace(anchor, anchor + "\n" + row93.rstrip(), 1)

io.open(P, "w", encoding="utf-8", newline="").write(s)
import hashlib
print("order rewritten:", "17:3x 重排" in s, "| R93 row:", "新28" in s)
print("md5", hashlib.md5(io.open(P, "rb").read()).hexdigest())
