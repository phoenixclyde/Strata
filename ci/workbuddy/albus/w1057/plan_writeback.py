#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1057: queue first-tier update (R74 done), denominator, writeback block + dir row.
import io
import re

P = r"D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()

# 1) denominator
old = "| 进度分母 | **530 条 / 已结 442 / 83.4%**（W1056；值由 `tools/progress.py` 派生，`tools/audit_scope.py §D` 拦手写） |"
new = "| 进度分母 | **532 条 / 已结 445 / 83.6%**（W1057；值由 `tools/progress.py` 派生，`tools/audit_scope.py §D` 拦手写） |"
assert old in s
s = s.replace(old, new, 1)

# 2) queue cell: R74 closed -> first tier becomes R91 -> R101
old_q = "**第一（代码移植 + 前置门，2026-11-08 机主指令：优先推进代码相关的以及前置项）**：**R74**（W4A4 离线精度门，不动内核——R91 的前置） → **R91**（dot8 接入 P1–P6，过门才动内核） → **R101**（#31247 cherry-pick，`quantize.cu` 的 DS4 分支同步改）"
new_q = "**第一（代码移植 + 前置门，2026-11-08 机主指令：优先推进代码相关的以及前置项）**：~~R74~~ **已过门（W1057，KL 0.0023/top-1 100%，`P583`）** → **R91**（dot8 接入 P1–P6；P2 前置=dot8 同访问面微基准，P4 复核=max KL 口径 0.0067） → **R101**（#31247 cherry-pick，`quantize.cu` 的 DS4 分支同步改）"
assert old_q in s
s = s.replace(old_q, new_q, 1)

# 3) directory row after W1056 dir row
anchor = ("| `回写 · W1056（2026-11-08 15:5x–16:4x）R116 微基准判否 + 唯一队列按代码优先重排` | "
          "同访问面三臂全 <1.3x（上界 1.264x）；PV fold=访存瓶颈；队列重排（机主令） | W1056 |")
assert anchor in s
dir_row = ("| `回写 · W1057（2026-11-08 17:2x–17:5x）R74 W4A4 精度门过门 + CPU-share 假阴性复盘` | "
           "KL mean 0.0023/top-1 100% 过门，R91 放行；CPU-share 旁路量化器教训入技能 | W1057 |")
s = s.replace(anchor, anchor + "\n" + dir_row, 1)

# 4) block before W1056 block
block_anchor = "### 回写 · W1056（2026-11-08 15:5x–16:4x）R116 微基准判否 + 唯一队列按代码优先重排"
assert block_anchor in s
block = """### 回写 · W1057（2026-11-08 17:2x–17:5x）R74 W4A4 精度门过门 + CPU-share 假阴性复盘

- **R74 过门（`P583`）**：QDQ 仿真探针 `strata-0.1.57-a4probe`（`quantize_mmq_q8_1` 加 env 门控 `STRATA_A4_SIM`：激活 int4 语义 codes 进 Q8_1 容器，MMQ 计算零改动；a4=0 逐位惰性）+ 4 臂窗口 logits 对拍（`STRATA_DUMP_FIRST_LOGITS` 248,320 维 × 6 prompt）：地板 0.000000（确定性）、惰性 0.000000、**B 臂 KL mean 0.002295 / top-1 100% ⇒ 过门（≤0.005 / ≥99%）**；max 0.006704（req3）超线 1.34× 记档为 R91 P4 复核项。R91 dot8 工程放行。
- **假阴性复盘（`P584`）**：run-1 用生产 `STRATA_PREFILL_CPU_SHARE=auto`，小 prompt GEMM 走 host 侧，CUDA 量化器被旁路——24 dump 逐对逐位同，门会以 KL=0 放行从未生效的候选。修法=quant_quality 技能偏差集的 `CPU_SHARE=0`（run-2 立即分化）。教训入库：**技能的偏差集是判据的一部分**；数值 A/B 必须强制 GPU 路径 + md5 矩阵自证臂间分化。req0 首请求路径 a4 无效应登记为已知空洞（5/6 点有效）。
- **窗口与生产**：4 臂 ×2 轮窗口，重启 10 次 / 停机 ≈480 s，trap=cp cfg+冷重启两次均还原（config md5 `8d234fa3…`、引擎 `05330748…` 复测一致）；探针生产未装。队列第一梯队更新为 R91→R101。进度 532 条 / 已结 445 / 83.6%。

"""
s = s.replace(block_anchor, block + block_anchor, 1)

# 5) block count line
d_i = s.find("### 6.5.0")
c_i = s.find("共 **", d_i)
assert d_i > 0 and c_i > d_i
n_rows = len(re.findall(r"^#{2,3}\s+(?:§6\.5\s+)?回写\s*·", s, re.M))
old_count = re.search(r"共 \*\*(\d+)\*\* 块", s[c_i:c_i + 80])
assert old_count
s = s[:c_i] + s[c_i:c_i + 80].replace(old_count.group(0), "共 **%d** 块" % n_rows, 1) + s[c_i + 80:]
print("count ->", n_rows, "(was", old_count.group(1) + ")")

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("W1057 plan writeback done")
