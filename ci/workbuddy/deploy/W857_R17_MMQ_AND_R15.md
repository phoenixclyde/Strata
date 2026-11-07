# W857 · R17 结案：48/48 层走 MMQ —— `dequant` 不是反量化；R15 负对照：ring 不是约束

> ⚠️ **降级（AUDIT17 P1-1，2026-11-01 15:2x 由 W863 补）**：标题与 §0 的「**ring 不是约束**」降级为
> **UNRESOLVED**，不再是定论。理由（本件 §1 自己就写了）：B 臂的 TIMING 被脚本 bug 冲掉、只剩 read 三档，
> 且**每档 1 次、无 repeat**（A 臂是 2 warm + 1 rep）；read 是端到端墙钟，本项目基线上 read 的 spread 本来就大
> （AUDIT13 P0-2 记过 `read1300` 3/3 同向被误判的先例）。
> **R17（48/48 层走 MMQ）那部分不受影响**，仍是本件最硬的结论。
> 要结 R15 需要重跑：两臂都要 TIMING，且每档 ≥2 rep、交错。

> 2026-11-01 00:47–01:2x。一次停服（2 臂 + 1 次恢复），按 §6.5 的"战线集中"把 R17 与 R15 合并跑。
> 生产已回到 `0.1.55g`（`29b15bb4…`），`TIP-OK` / `GATE PASS`。

## 0 两句话

1. **`strata: prompt experts: MMQ 48 / fused 0 / FP16 0 of 48 layers (no fallback)`** —— 生产 48 层**全部**走 MMQ。
   ⇒ 相位里的 `dequant` **不是**"专家权重重反量化成 FP16"，而是 **group gather + q8_1 激活量化**。
   W853 §3.1「Q4_K→FP16 写进 DQ ring」与 R14「dequant 能不能摊薄」**双双作废**。
2. **ring 深度不是 `wait copy` 的约束**：把 `STRATA_PREFILL_RING` 钉到 8（STAGE）后，
   read 三档 253/1167/1919 tok = **1.43 / 2.82 / 3.72 s，与默认 ring 完全相同**。

## 1 实验（2 臂，各含 2 warm + 1 rep/档，只用 rep0）

| 臂 | 二进制 | TIMING | ring | 结果 |
|---|---|---|---|---|
| A | `strata-0.1.55-banner`（`a10af384…`，= 生产 + 1 行 printf） | 1 | 默认（≥1024 tok 时 96/384/1024） | banner + 相位表 ✔️ |
| B | `0.1.55g` | **丢了**（脚本 bug） | `STRATA_PREFILL_RING=8` | 只有 read 三档 |
| 恢复 | `0.1.55g` | 关 | 默认 | ready 后 `TIP-OK` / `GATE PASS` |

**脚本 bug（记下来）**：`setenv()` 从 `/tmp/w857_cfg_base.json` 重建配置，于是 B 臂把 A 臂的
`exe=banner` 和 `STRATA_PREFILL_TIMING=1` 一起冲掉了。⇒ **改 env 必须基于"当前配置"而不是"基线配置"**；
要改多个键就一次改完。

## 2 A 臂的相位（rep0，与 W853 的 rep0 复现一致）

| 相位 | 253 tok | 1167 tok | 1919 tok |
|---|---:|---:|---:|
| gemm gate/up | 204 (18.9%) | 525 (21.5%) | 740 (22.3%) |
| gemm down | 143 (13.3%) | 337 (13.8%) | 464 (14.0%) |
| **dequant（gather + q8 量化）** | **216 (20.0%)** | 292 (12.0%) | **317 (9.6%)** |
| **wait copy（等 blob 拷贝事件）** | **137 (12.7%)** | 287 (11.8%) | **288 (8.7%)** |
| gdn | 67 | 219 | 319 |
| qsa attn | 9 | 95 | 223 |
| host staging | 92 ms | 354 ms | 560 ms |
| GPU / wall | 1081/1084 | 2440/2451 | 3315/3331 |

⇒ `gather + wait copy + q8 量化` 在 1919 tok 上合计 **605 ms / 3315 ms = 18.2%**，在 253 tok 上 **353 ms / 1084 = 32.6%**。
**短请求上"搬运"比"算"更贵**，这解释了"短 prompt 每 token 贵 2.5×"。

## 3 `dequant` 到底是什么（源码钉死）

MMQ 路径里每个专家的时间线（`prefill.cpp:5191-5240`）：

```
pt.mark(kPfWaitCopy) → wait_copied(最后一个 blob) → pt.mark(kPfDequant)
  → gather_native_group(...)     // 把专家字节搬进 16 专家组缓冲（可能顺带转格式）
  ...
compute(): pt.mark(kPfDequant) → mmq::quantize(q8_1 激活) → pt.mark(kPfGemmGU) → MMQ 启动
```

所以 `dequant` 名字是历史遗留：它量的是**搬运 + 激活量化**，与"权重反量化"无关。
W795 当时就写过「dequant（实为 group gather）」，W853 又按 FP16 路径解释了一遍——现在有 banner 直接否掉。

## 4 对队列的影响（已改）

| 项 | 变化 |
|---|---|
| **R14** | **DONE_NEG（前提作废）**：没有反量化可摊薄 |
| **R15** | 结论：**ring 深度不是约束**；相位证据缺（B 臂丢 TIMING），并入 R5 的 A/B 一起取 |
| **R17** | **DONE**：三路层数已拿到（48/0/0） |
| **R5（#4283 routed stream）** | **升为第 1 序**：它直接减少"拷贝量"，正对 18.2% 这块 |
| **P1c / X2** | 降权：`--pcie-frac` 是**解码侧**旋钮（`verify.cpp:2276`：the PCIe share is pcie_frac of **the misses**），与 prefill 的 wait copy 无关 |

## 5 #4283 的实测（2026-11-01 复核上游正文，不是转述）

- opt-in `STRATA_PREFILL_ROUTED_STREAM=1`，默认路径一字不改；+665/−8，5 文件，含 no-GPU 测试。
- RTX 3090：后续轮读 3,214→2,640 ms（**−17.9%**）；1979 tok **+19.9%**、3963 +8.2%、6011 +2.1%、32105 +5.3%。
- **同作者 HIP 机（2×RX 6900 XT / ROCm 10.0）：2K/4K 持平，8K–32K 慢 0.7–4.2%** —— 这条必须带进判据。
- 作用条件：单 GPU、流式 chunk（ring > 8、≥1024 tok）、issuer 开着；融合路径 / peer ring 下不生效。
- 跳过量随 prompt 变长而衰减：1,046 tok 跳过 42%，4,867 跳过 14%，31,473 跳过 3%。

⇒ 我们的短读（1–2K）正是它最有效的区间；但 gfx906 的 HIP 表现**没有任何人测过**，
所以判据必须含"8K 不回退 >2%"。

## 6 生产（已恢复并验证）

| 项 | 值 |
|---|---|
| 容器 | `strata166-407`，started `2026-10-31T16:58:16Z`，restarts=0 |
| 引擎 | `/data/bin/strata-0.1.55g`（`29b15bb4…`）= `gfx029-build/strata`（PROVENANCE 一致） |
| 配置 | `exe=/data/bin/strata-0.1.55g`，env **6** 条（TIMING / RING 已移除） |
| 校验 | **TIP-OK**（`aef9d256`）+ **GATE PASS**；`/health` ok；`920 MiB VRAM free` |

**恢复过程的一个坑**：`docker stop/start` 之后 serve 第一次起的引擎没到 ready 就退了（docker `restarts=0`、
看不到 traceback），第二次才起来，整体 **≈14 min**（平时 250–300 s）。这段期间 `/health` 一直空。
⇒ 恢复脚本的 `wait_health` 余量要按 **≥900 s** 给，且要打印"第几次尝试"。
