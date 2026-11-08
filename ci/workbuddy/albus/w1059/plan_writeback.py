#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1059 plan writeback: queue cell (first tier closed, new order) + denominator + block + directory.
import io
import re

P = "D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()

# 1) queue cell: first tier fully closed in W1059
old_q = ("**R91**（P0–P4 已结 `P585`–`P588`：P1 逐位/P3 等价+ISA/P4 均值口径过门；P2 前置门 1.57× 过但纯指令密度 0.96× 判否；"
         "**P2/P5 待 x_qs 流量占比侦察 `P589`**） → **R101**（#31247 cherry-pick，`quantize.cu` 的 DS4 分支同步改）")
new_q = ("~~R91~~ **DONE_NEG（W1059：P0–P4 全过、P2 判否 ROI 上界 0.7–2.05%<2×CV，`P587`/`P589`）** → "
         "~~R101~~ **DONE（W1059：#31247 已在本树、单变量 KL 0.104 定案，`P591`）**　"
         "**第一（现行）**：**R46**（attention 效率，上限 3.3×；下一手=STRATA_QSA_DUMP 重建录）> **R60**（stream-k，R59 门已过；下一手=gcn 表 11 行翻 true + 32K/64K 3rep + KL）")
assert old_q in s, "queue segment not found"
s = s.replace(old_q, new_q, 1)

# also update the second-tier marker so the queue reads coherently
old_t2 = "**第二（prefill 代码手段；R85 验收随行）**：**R85**（长档 801→850 tok/s 端到端验收口径）→ 手段序 **R46**（attention 效率，上限 3.3×）> **R64**（Q.K int8；**前置**：32K/131K attention 占比实测）> **R60**（stream-k；**前置**：R59 KL≤0.005+top-1≥99%）"
new_t2 = "**第二**：**R89**（depth 1×/3×/6× 绝对 ms）→ **R95**（P309 busy/phase）→ **R86**（~~已判否：立项门 −2.6~−3.3%<5%，W1059~~）；~~R64~~（已判否：32K 占比 15.3%<25%，W1059）；R85 验收随行（801→≥850）"
assert old_t2 in s, "tier2 not found"
s = s.replace(old_t2, new_t2, 1)

# 2) denominator
old_d = "| 进度分母 | **537 条 / 已结 450 / 83.8%**（W1058；值由 `tools/progress.py` 派生，`tools/audit_scope.py §D` 拦手写） |"
new_d = "| 进度分母 | **540 条 / 已结 488 / 90.4%**（W1059；值由 `tools/progress.py` 派生，`tools/audit_scope.py §D` 拦手写） |"
assert old_d in s, "denominator row not found"
s = s.replace(old_d, new_d, 1)

# 3) writeback block (newest first)
BLOCK = """### 回写 · W1059（2026-11-08 19:0x–19:5x）待办大清扫：+38 收口（P392 KL=0 / R101 定案 / R91·R86·R64 判否）

- **P392 LOGPOS 数值门 PASS（`P590`，KL=0）**：K10 整栈（#29953/#30168/#30553）与基线**逐位等价**（kl_prop mean/max 0.000000、TSV md5 同）——P407 源码等价获运行期实证；配 P390 速度免费 ⇒ 整栈可零代价拿，#29953 数值欠账闭案。
- **R101 定案（`P591`）**：#31247（上游 `8fc0376`，已上网核实）的 Σx→d·Σq 语义**已在本树**（`quantize.cu:521`）⇒ cherry-pick 空操作；单变量探针（`strata-0.1.57-sumx`，STRATA_SUMX env 门控）实测该差异**非平凡**（KL mean 0.104 / max 4.37 / top1 58/60）⇒ 一致性修正在正确侧，本树已在正确侧。
- **协议缺陷（`P592`）**：首臂 expert-profile 生成态效应 KL 0.0044/max 0.161（top1 全同）⇒ 数值窗口地板对必须用 profile 就位后的臂或先空跑暖 profile；跨容器确定性另有实证（不同二进制逐字节同）。
- **判否族（存量臂/上界算术，38 项收口）**：R91 dot8（ROI 上界 0.7–2.05%<2×CV，P587/P589）、R84 并案、R64（32K attn 15.3–19.0%<25%）、R86 族×4（down-only −2.6~−3.3%<5% 立项门）、R81（d4+ 桶 0/0 + W809 六臂 6<4）、R39/R94/R19/R50/G 族/P 族/X 族等（详见 `P585`–`P592` 与 land_census 族账本行）。
- **两坑入库**：①CMake configure **重写 overlay**（checkout 触发 reconfigure 静默洗补丁）⇒ 两段式构建 + 字符串断言进二进制；②nvfp4/mxfp4 共享 launch 形态 ⇒ 补丁替换按内核名锚定。
- **生产**：换件 0 / config 改 0（窗口臂独立 cfg）/ 重启 1 次 / 停机 ≈500 s（五臂 LOGPOS 窗口，trap 还原绿、md5 复测一致）。进度 540 条 / 已结 488 / 90.4%。

"""
anchor = "### 回写 · W1058（"
assert anchor in s
s = s.replace(anchor, BLOCK + anchor, 1)

# 4) directory row + block count
dir_row = ("| `回写 · W1059（2026-11-08 19:0x–19:5x）待办大清扫：+38 收口（P392 KL=0 / R101 定案 / R91·R86·R64 判否）` | "
           "P392 整栈 KL=0；R101 已在树+KL 0.104 定案；R91/R86 族/R64/R81 判否；38 项收口；首臂 profile 污染登记 | W1059 |")
d_anchor = "| `回写 · W1058（2026-11-08 18:2x–19:0x）R91 P0–P4 全过门 + dot8 收益定位在布局侧` | P1/P3/P4 过门；ISA 5184→0/2528；纯密度 0.96× 判否、布局 1.57× 过门；P2 待占比侦察 | W1058 |"
assert d_anchor in s
s = s.replace(d_anchor, d_anchor + "\n" + dir_row, 1)

old_c = "共 **55** 块"
assert old_c in s
s = s.replace(old_c, "共 **56** 块", 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("writeback applied")
hdrs = re.findall(r"^#{2,3}\s+(?:§6\.5\s+)?回写\s*·", s, re.M)
print("block headers:", len(hdrs))
