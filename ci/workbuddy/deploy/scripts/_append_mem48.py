# -*- coding: utf-8 -*-
"""追加 [W-Strata-28]：预填分解诊断（推翻 PLE 假说）+ 官方文档/社区报告的关键结论。"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')

P = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-07.md'
TXT = """

## [W-Strata-28] 预填分解终于拿到 —— **PLE 假说被证伪**；预填 ~92% 是 GPU 计算

**手段**：一次性 `generate` 模式（`--pack --tokens-file /data/probe_tok.txt --max-new 4 --native <shard1> --spec 4 --spec-min-p 0.5 --resident-budget-gib 76 --expert-profile ... --expert-cache auto --max-context 131072 --kv int8`）。
**关键**：`--tokens-file PATH` 是一次性模式的入口；**`--spec T` 必填**（漏了会被拒："is a native (IQ) pack: it needs --native SHARD1, --spec T (T >= 2) and --prefill CHUNK"）。
脚本 `D:\\strata166\\scripts\\_diag_prefill166.py`，日志 `_diag_prefill.txt`。

**引擎自带的分解行**（`generate.cpp:10210`，`fprintf(stderr)`，**只在一次性模式打**）：

| Arm | prefill | PLE | host(DMA) | 说明 |
|---|---|---|---|---|
| `--prefill auto`（=8192，2 chunks） | **35213.3 ms / 465.3 tok/s** | **1937.3 ms（5.5%）** | 403.9 ms（1.1%） | 基准 |
| `--prefill auto:32768`（1 chunk 16383） | 35820.7 ms / **457.4 tok/s** | 1760.8 ms | 198.9 ms | **更慢 ⇒ 大 chunk 无益，已排除** |

`ple io: 262336 rows, 0.0% row-cache hits, 259831 SSD reads (1087.2 MB), read p50 4850 us p99 5671 us,
blocked 4885.592 ms total (submit 42.141 ms)` ⇒
- **16 rows/token 得到证实**（262336 / 16383 = 16.0）
- 单行 p50 **4.85 ms**（慢得离谱）但 259831 次读只 blocked 4885 ms ⇒ 并发 ~258（= `--ple-inflight` 默认 256），**I/O 已被算力盖住**
- **PLE 只暴露 1937 ms / 35213 ms = 5.5%** ⇒ **「PLE 取行是预填瓶颈」正式证伪**（此前我两次把它当最大嫌疑，都是错的）
⇒ **~92-93% 是 GPU 计算**（attention/dense/PLE block/专家 MMQ）。MMQ 关掉掉 19% ⇒ 专家 GEMM ≈ 19%，其余 ≈ 73% 是别的 GPU 核。

**另一条副产品**：同一次运行的 `--stats` 打出 **`the CPU expert pool 27.490 ms/token over 48 layers`**（`pool phases drain 26.095 ms/token`）⇒ **解码里 CPU 专家池是大头**。对照官方 MI50 社区报告"experts 全在 VRAM、CPU 池算 0 个"⇒ 这是 1×32GB 装不下 24576 专家的代价。

## 官方文档/社区报告（都在源码包里，`bench/results/` 与 `docs/`）

- **`bench/results/2026-09-28-prefill-speed/README.md`**（预填专题，572→1290 tok/s 的 7 步）：buffers 复用 / PLE 行在独立线程预读下一 chunk / `--prefill auto` 自适应 chunk（8192>6144>4096）/ host 拷贝交给 helper 线程 / **PLE 整块算（两个 GEMM）而非逐 token** / MMQ 替代 反量化+cuBLAS / **chunk≥2048 时非驻留专家走环形流水**。**全部已在 0.1.13+，我们是 0.1.40 ⇒ 默认全开。**
- **`bench/results/2026-10-03-community-2x-mi50/README.md`**（作者 JeanP00l，2×MI50 16GB + E5-2666v3，**Coder IQ1_M**，`--prefill 4096`，layer_split 27，**12288 专家全在 VRAM**、`--kv int8 --kv-resident 32768`、`STRATA_ARENA_MMAP=1`、`--pcie-frac 0`、`--vram-reserve-mib 600`）：prompt **320.9 / 522.8 / 516.8**，decode **50.1 / 47.8 / 45.7**，命中率 **100%**。
- 我方（1×MI50 32GB、24576 专家、IQ4_XS、`--prefill auto`）：prompt **438.8**、decode **42.9** ⇒ **单卡 vs 双卡不落下风**；差距主要来自对方**专家只有一半（12288）+ 1-bit**。
- 源码确认存在的旋钮（尚未试）：**`STRATA_ARENA_MMAP`**、**`STRATA_PREFILL_RING`**、`--vram-reserve-mib`（默认 700）、`--no-prefill-borrow`、`--no-split-rows`、`--shared-late`、`--no-pool`、`--pool-workers`。

**已排除清单（今天新增）**：`--prefill auto:32768`（457.4 < 465.3）、`--no-ple`（与 `--native` 冲突启动被拒）、`--no-pool`（启动后未出分解，待重试）。
"""
open(P, 'a', encoding='utf-8').write(TXT)
print('appended, size =', os.path.getsize(P), 'B')
