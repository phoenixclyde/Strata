# -*- coding: utf-8 -*-
"""追加 2026-10-06 日志：预填天花板分析（含官方 gfx1100 对照锚点）"""
import os

p = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-06.md'
TXT = """

## [W-Strata-14] 预填还能涨多少 —— 可用对照锚点与剩余杠杆（含官方同规模实测）

### 一、位置：433~439 tok/s ≈ 2.3 ms/token，8k→72k prompt 长度线性无衰减
（`--ple-inflight 2048` 拿到 439.4 是本轮最高，但 +0.5% = 噪声，不计收益）

### 二、[!] 关键的官方对照锚点（`docs/AMD_HIP_PERFORMANCE.md`）
官方在 **RX 7900 XTX 24GB + Ryzen 9 7950X3D + 64GB + ROCm 7.1** 上、**同引擎同 prompt 路径**实测：

| 请求（temper 0 / reasoning disabled / 128-token cap） | 预填 t/s |
|---|---|
| 4,210 token 首用 | **447.5** |
| 8,830 token 首用 | **873.7** |
| 4,210 token 已热 | **901.1** |
| 8,830 token 已热 | **966.5** |

- 官方自己对比的是"**他们旧的 HIP 运行时**"：240/484/457/478 ⇒ **新 HIP MMQ 路径 1.80~2.02×**
- 他们那台的模型是 **Orca Flash Next IQ3_XXS**（**i-quant**），测量口径明确写了：
  `--mmap-experts --resident-cpu-experts`、固定 `--expert-profile`、`--expert-cache auto`、`--prefill 8192`、
  `--max-context 262144`、`--kv int8 --kv-resident 32768`、`--pool-workers 15`、**`--adapt-every 0`**、**`--pcie-frac 0`**、
  `--vram-reserve-mib 1024`；环境变量 `STRATA_PREFILL_MMQ=1`、`STRATA_HIPBLASLT_TUNING=<gfx1100 表>`、
  `STRATA_PREFILL_RING=96`、`STRATA_IO_THREADS=32`

⇒ **我们 436~439 vs 他们 874~966（8830 token）≈ 2.1×**。差距要拆成三块归因，别整块当成"可优化空间"：
1. **硬件**：gfx1100（RDNA3）的 int8/fp16 吞吐量级高于 gfx906（Vega20）—— 这一项占大头
2. **量化档**：他们是 **i-quant（IQ3_XXS）**，走原生支持的 prompt kernel；我们是 **K-quant（UD-Q4_K_XL）**，
   走"CUDA 内核 + hip_compat 垫片"；且 IQ3_XXS 专家约 47 GB < 我们 71.8 GiB
3. **配置口径**：他们明确设了 `--adapt-every 0`（**关掉请求期的自适应换入换出**）和 `--pcie-frac 0`，我们基本是默认

### 三、剩余杠杆（按预期收益排序，含"已排除"）
| 杠杆 | 状态 |
|---|---|
| `--adapt-every 0` | **未测，最高预期** —— 官方测量口径里特意设了它；我们默认 4，请求期间在 VRAM↔RAM 搬专家，prompt 期白付成本 |
| `--pcie-frac 0` | 第四轮已测（结果待读） |
| `--prefill 16384` / `--prefill 8192` 固定 | 第四轮已测（官方结论：静态 16K chunk **无明显端到端收益**） |
| `STRATA_PREFILL_RING`(96) / `STRATA_IO_THREADS`(32) / `--vram-reserve-mib` / `--pool-workers` | 未测 |
| `--ple-io ram/mmap`、`STRATA_KQ256`、`STRATA_PREFILL_MMQ=0` | **已排除**（ram 慢 48%、mmap 噪声、KQ256 噪声、MMQ=0 慢 19% 即 MMQ 有效） |
| 换 **i-quant 档**（UD-IQ4_XS 93.7GB / IQ3_XXS 75.8GB） | **未做，唯一有官方同规模背书的提速路径**（Strix Halo 上 UD-IQ4_XS 实测 prompt ~820 tok/s） |
| 移植/写 kernel | **暂不做** —— 关掉整个 MMQ 才掉 19%，盲改期望收益小；先拿到 `prefill ... PLE P ms` 分解再定 |

### 四、当前最该做的一件事
用**一次性 `generate` 模式**（`--tokens-file`，token id 由容器内 tokenizer 生成）跑出
`strata generate: prefill N tokens in C chunks, X ms; experts streamed S (D by DMA, host H ms), resident R; PLE P ms`
—— 这行在 `--serve` 下不打（实测 "chunks" 0 次）。拿到 `PLE P ms` 与 `host H ms` 才能把 2.3 ms/token 切开。
"""
old = open(p, encoding='utf-8').read()
open(p, 'w', encoding='utf-8').write(old.rstrip() + '\n' + TXT)
print('appended, size', os.path.getsize(p), 'B')
