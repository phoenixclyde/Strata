#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1058 plan writeback: queue cell (R91 state) + denominator + writeback block + directory.
import io
import re

P = "D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()

# 1) queue cell: R91 segment reflects P0-P4 closed + P2/P5 pending recon
old_q = "**R91**（dot8 接入 P1–P6；P2 前置=dot8 同访问面微基准，P4 复核=max KL 口径 0.0067）"
new_q = ("**R91**（P0–P4 已结 `P585`–`P588`：P1 逐位/P3 等价+ISA/P4 均值口径过门；P2 前置门 1.57× 过但纯指令密度 0.96× 判否；"
         "**P2/P5 待 x_qs 流量占比侦察 `P589`**）")
assert old_q in s, "queue segment not found"
s = s.replace(old_q, new_q, 1)

# 2) denominator (gate 5 compares to PROGRESS sums: 537/450)
old_d = "| 进度分母 | **532 条 / 已结 445 / 83.6%**（W1057；值由 `tools/progress.py` 派生，`tools/audit_scope.py §D` 拦手写） |"
new_d = "| 进度分母 | **537 条 / 已结 450 / 83.8%**（W1058；值由 `tools/progress.py` 派生，`tools/audit_scope.py §D` 拦手写） |"
assert old_d in s, "denominator row not found"
s = s.replace(old_d, new_d, 1)

# 3) writeback block (newest first: insert before the W1057 block)
BLOCK = """### 回写 · W1058（2026-11-08 18:2x–19:0x）R91 P0–P4 全过门 + dot8 收益定位在布局侧

- **P1 量化器（`P585`）**：BlockA4 = {half d; int16 sa; uint8 qs[16]}——scale=amax/7、roundf、clamp [−8,7]、**裸整数 Σa 进块头**（区别于 Q8_1 的 d·Σq fp16：sdot8 重定心 +8·Σa 需 int32 域裸整数）；公式逐字对齐 a4sim（R74 门测式）。CPU/GPU 逐位一致 4096/4096 块（含 tie/饱和边角），mismatch=0。
- **P3 vec_dot + ISA（`P586`）**：`vec_dot_q4_K_q4_impl_mmq` = `sdot8(q^0x88888888, a) + 8·Σa`（min 项乘 Σa）——三臂 GEMM 81920/81920 逐位等价。真 Q4_K 实例 ISA A/B（编译命令逐字抄 ninja）：**v_dot4 5184→0、v_dot8 0→2528**（2.05:1，判据「减半且 >0」超预期）；fatbin 管道复现 P519 外证。**接线陷阱**：mmq-instance 相对 include `../mmq.cuh` 直读 llama-master 树，overlay 头对实例 TU 是 no-op（W1057 的 a4sim 有效只因 quantize.cu 是直接 TU）——改内核头必须打 llama-master 树副本。
- **P2 前置微基准（`P587`）**：同访问面三臂（权重行 LDS 缓存，3 run×5 trial，CV 6–7%）：A_dp4a 0.83 TMAC/s、B_repack **0.962×**、C_packed **1.570×**。**纯指令密度 ≈0 转化（B 臂），收益全部来自布局流量减半**——「换更强指令不改布局=白干」的第二例证（第一例=R116）。P2 前置门过。
- **P4 精度门（`P588`）**：均值口径 **PASS**（组合链：R74 logits KL mean 0.002295 / top-1 100% + P1↔a4sim 公式同一 + P3 整数逐位等价 ⇒ 真 W4A4+dot8 数值 = 门测仿真数值）；max 0.006704 复核按 W913/R59 注册口径（mean 门、max 记档；R59 自身 max 0.011209 过门）记档不判死——**W951「P4 大概率是终点」的预判被实测推翻**。
- **P2/P5 立项分析（`P589`）**：W943 的 −2.05% 上限是指令口径，其密度转化假设被 B 臂证伪；真候选收益=布局/流量侧（C 臂 1.57×），真核 x_qs 流量占比未量；P5 门（2×CV=3.2%）对 1.5–2% 效应不可检（W914 纪律③记「未测出」）。**预注册下一步**：先做 x_qs 流量占比侦察（PMC/LDS 计数）再裁 P2；若要 P5 可检须 CV≤0.75%（重复 ×4–5）或改层级指标验收。tile 手术暂不开工。
- **生产**：零变更（scratch 容器/单 TU 编译，overlay 与 llama-master 双份 md5 还原 9e0da3cb）；无重启无停机。进度 537 条 / 已结 450 / 83.8%。

"""
anchor = "### 回写 · W1057（"
assert anchor in s
s = s.replace(anchor, BLOCK + anchor, 1)

# 4) directory row after the W1057 directory row + block count 54 -> 55
dir_row = ("| `回写 · W1058（2026-11-08 18:2x–19:0x）R91 P0–P4 全过门 + dot8 收益定位在布局侧` | "
           "P1/P3/P4 过门；ISA 5184→0/2528；纯密度 0.96× 判否、布局 1.57× 过门；P2 待占比侦察 | W1058 |")
d_anchor = "| `回写 · W1057（2026-11-08 17:2x–17:5x）R74 W4A4 精度门过门 + CPU-share 假阴性复盘` | KL mean 0.0023/top-1 100% 过门，R91 放行；CPU-share 旁路量化器教训入技能 | W1057 |"
assert d_anchor in s
s = s.replace(d_anchor, d_anchor + "\n" + dir_row, 1)

old_c = "共 **54** 块"
assert old_c in s
s = s.replace(old_c, "共 **55** 块", 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("writeback applied")
# self-check counts
hdrs = re.findall(r"^#{2,3}\s+(?:§6\.5\s+)?回写\s*·", s, re.M)
print("block headers:", len(hdrs))
