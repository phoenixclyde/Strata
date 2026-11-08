#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1056: add the W1056 writeback block + directory row in W832 §6.5/§6.5.0.
import io
import re

P = r"D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()

# 1) directory row: insert after the W1055 directory row
anchor = "| `回写 · W1055（2026-11-08 14:5x–15:3x）dot4 软路径探针 + wave64 盘点 + R116 预算` | marker=0 证伪软路径；R52 前提证伪；R116 预算 0.26% | W1055 |"
assert anchor in s, "W1055 dir row not found"
dir_row = ("| `回写 · W1056（2026-11-08 15:5x–16:4x）R116 微基准判否 + 唯一队列按代码优先重排` | "
           "同访问面三臂全 <1.3x（上界 1.264x）；PV fold=访存瓶颈；队列重排（机主令） | W1056 |")
s = s.replace(anchor, anchor + "\n" + dir_row, 1)

# 2) block: insert before the W1055 block header
block_anchor = "### 回写 · W1055（2026-11-08 14:5x–15:3x）dot4 软路径毒化探针 + wave64 盘点 + R116 预算"
assert block_anchor in s, "W1055 block not found"
block = """### 回写 · W1056（2026-11-08 15:5x–16:4x）R116 微基准判否 + 唯一队列按代码优先重排

- **R116 判否（`P581`）**：微基准 `albus/w1056/pv_micro_r116.cu`（生产 fold 形状：CHUNK=64×G=12×HD=256、Q4_0 V 池 18B/32 值、thread=d、cell-major P、4-cell V 组载）对拍 dot4 三臂，3 run×5 trial 交错：**A_fp32 0.0270 / B_dot4_pre 0.0214（1.264x）/ C_dot4_live 0.0264（1.022x）/ D_dot4_v8 0.0216（1.248x）**，三臂全 < 预注册 1.3x 门 ⇒ 不接 OPT。正确性：dot4 臂 vs CPU 同方案参考 rel_err 5.8e-8。**结构结论：PV fold 是访存/延迟瓶颈**，dot4 指令密度 4x 只转化 1.264x；P 在途量化再吃 23%；「V nibble→int8 流量 ×2」在该形状近免费（D vs B −1.3%）。R110→R112→R116 的 k8v4 V 侧 dot 化整线关闭。
- **队列重排（`P582`，机主 2026-11-08「优先推进代码相关的以及前置项」）**：§0.1 重写为 第一（代码+前置）R74→R91→R101；第二（prefill 代码手段，R85 验收随行）R46>R64>R60；第三 R89→R95→R86；代码存量候选入册（P455/P481/P424/R63/G1–G10/D28/M2/K8/U2/U4/X3–X7/P1c）；治理 R80/R79/R81 排后。前置链显式：R60←R59、R64←占比实测、R86←R95 后且 ≥5%、R63←R61。举一反三：R91 动 P2 前须补 dot8 同访问面微基准（防「密度 4x 收益 1.26x」重演）。
- **生产零变更**：装机 0 / 重启 0 次 / 停机 0 s / 回滚 0；微基准全在 scratch 一次性容器。进度 530 条 / 已结 442 / 83.4%。

"""
s = s.replace(block_anchor, block + block_anchor, 1)

# 3) fix the stale block count line in §6.5.0 footer (must locate after the directory)
d_i = s.find("### 6.5.0")
c_i = s.find("共 **", d_i)
assert d_i > 0 and c_i > d_i, "count line not found after directory"
# "块" = writeback blocks; count exactly what plan_single_source counts (##/### 回写 · headers)
n_rows = len(re.findall(r"^#{2,3}\s+(?:§6\.5\s+)?回写\s*·", s, re.M))
old_count = re.search(r"共 \*\*(\d+)\*\* 块", s[c_i:c_i + 80])
assert old_count, "count pattern missing"
s = s[:c_i] + s[c_i:c_i + 80].replace(old_count.group(0), "共 **%d** 块" % n_rows, 1) + s[c_i + 80:]
print("count line ->", n_rows, "(was", old_count.group(1) + ")")

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("W1056 block + dir row inserted")
