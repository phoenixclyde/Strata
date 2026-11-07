# -*- coding: utf-8 -*-
"""追加 2026-10-06 日志：MMQ/KQ256 A/B 实测 + PLE I/O 假设"""
import os

p = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-06.md'
TXT = """

## [W-Strata-12] 预填瓶颈定位：**MMQ 只是 1/6，真凶是 PLE 表的 IO 模式**

### 一、单变量 A/B（同机同配置，18,074-token 冷 prompt，每个 arm 重启后测）
配置：`--pack ud-q4_k_xl --native shard1 --resident-budget-gib 76 --expert-cache auto --prefill auto --spec 4 --spec-min-p 0.5 --mtp --max-context 131072 --kv int8`

| Arm | 环境变量/参数 | 预填 tok/s | 相对基线 | 解码 t/s |
|---|---|---|---|---|
| `baseline` | — | **436.6** | — | 25.2 |
| `restore`（基线复跑，验重复性） | — | **433.3** | −0.7% | 26.5 |
| `kq256` | `STRATA_KQ256=1` | 437.3 | **+0.2%（=噪声）** | 26.0 |
| `mmq_off` | `STRATA_PREFILL_MMQ=0` | **366.9** | **−19.0%** | 26.1 |

**两条硬结论**：
1. **MMQ 确实在生效、值约 19%**（这同时是对"MMQ 是否真被用上"的判定性实验 → 是）
2. 反过来推：**把 MMQ 整个换成 FP16 反量化 + hipBLAS 也只掉 19% ⇒ 专家 GEMM 在预填里只占约 1/6**
   ⇒ 瓶颈不在专家乘，**之前怀疑的"CPU 侧 K-quant 不是多 token"也被证伪**（`STRATA_KQ256=1` 零收益，
   说明预填期的专家行根本不是 CPU 池主导的）
3. 基线重复性很好（436.6 / 433.3，±0.7%），说明这套 A/B 方法本身可信

### 二、[!] 真凶指向 **PLE 表的读取模式**（源码级强证据）
- `src/program/generate.cpp:393-395` 原文：
  `/// The PLE gather's prefetch, as an A/B arm.  The gather measured **2.10-2.61 ms/token** because its sixteen`
  `/// row reads are sixteen SEPARATE page faults into a **26.8 GB mapping**`
- **换算验证**：166 实测 41.3 s / 18,074 token = **2.29 ms/token** —— **正中该区间**
  （关 MMQ 后 49.3 s → 2.73 ms/token，即专家 GEMM 约 +0.44 ms/token）
- 这也解释了此前所有线性现象：21.6k 与 71.8k 的 tok/s 几乎相同 ⇒ 每 token 常数开销主导
- **`--ple-io` 三档语义**（`generate.cpp:548-550`）：
  - `direct`（**默认**）：无缓冲 SSD 读，**表根本不进 RAM、不进文件缓存**
  - `mmap`：A/B 档，走页缓存
  - `ram`：**启动时把整张表 mlock 进 RAM**（Linux/macOS；Windows 上只有 mmap）
- 相关旋钮：`--ple-row-cache N`（默认 1048576 行 × 90 B ≈ 90 MB）、`--ple-inflight N`（默认 256）、
  `--ple-sync-submit`、`--no-ple-prefetch`（prefetch 默认开）
- **我们的条件**：PLE 表 26.8~28.8 GB，166 有 ~70 GB 空闲 RAM，容器以 `--ulimit memlock=-1` 启动 ⇒ `--ple-io ram` 具备条件
- **旁证**：官方在 **Strix Halo（gfx1151，128 GB 统一内存）** 用 UD-IQ4_XS 实测 prompt ~820 tok/s
  （= 1.22 ms/token）；统一内存意味着**它的 PLE 表本来就在 RAM 里** ⇒ 与"PLE 在 RAM 就快 2 倍"一致

### 三、其余待验旋钮（按预估收益排序）
1. `--ple-io ram` / `mmap`（**正在跑三档 A/B**）
2. `--pcie-frac`：自动 `0.55 × min(1, 13.1/20) = 0.36`（`generate.cpp:1222`）；可显式扫 0/0.2/0.36/0.55
   （预填期实测 `+5.6% of the routed experts over PCIe`）
3. `--ple-row-cache` 调大（跨轮对话有复用价值）、`--ple-inflight` 调大（SSD 并发）
4. `--pool-workers`（默认 21）、`--prefill` chunk、`--shared-late`、`--adapt-every`、`--pcie-mode`
5. `--stats`（per-stage 分解；`generate.cpp:413`）—— 下一步用它做最终确认

### 四、方法学沉淀（本轮有价值的副产物）
- **"重启型 A/B"的中间态极易被误读**：`kill → sleep 4 → 启动` 的窗口里进程全空、`curl` 回 000，
  看着像挂了其实是正常过渡 ⇒ 快照必须连拍两次或加上下文（如 server 存活秒数）再下结论
- 取数要抓**引擎日志里的 `prompt N tokens = ... read in X ms (Y tok/s)`**，那才是引擎自己的计时；
  HTTP 侧 wall time 含网络与排队，只能做交叉验证
"""
old = open(p, encoding='utf-8').read()
open(p, 'w', encoding='utf-8').write(old.rstrip() + '\n' + TXT)
print('appended, size', os.path.getsize(p), 'B')
