# W853 · M5：prefill 相位拆开了 —— 真正的成本不是 dense GEMM

> **⚠️ AUDIT16 大改（见 `deploy/AUDIT16_W844_W853.md` P0-1/2/3、P1-13、P2-18）**：
> ① **§2 的三行全部取自"重启后第 2 个 warm 请求"**（引擎 timing 墙钟 1184 / 2694 / 3863 ms），
>    实测 `rep0` 另有 1084 / 2453 / 3328 ms（248 / 1162 / 1914 tok）没被用；"各 3 次"实际是 `reps=1`，每档 n=1。
>    **相位百分比与绝对值请以 AUDIT16 §1-P0-1 的 rep0 表为准**：
>    dequant **216/289/315**、wait copy **137/290/293**、GU 204/524/735、down 143/335/462、staging 92/369/565。
> ② 因此"dequant 与 wait copy 都是固定成本"**只对 dequant 成立**；wait copy 是"涨 2.1× 后饱和"，
>    报告 §1 的"非单调 170→415→259"是 warm 样本的产物。
> ③ §3.2 的机理**读错了**：`prefill.cpp:3456` 是 D-5 "issuer 线程已消除旧等待"的解释性注释（过去时）；
>    `kPfWaitCopy` 埋点后跟的是 `wait_copied()` / `cudaStreamWaitEvent(copied[])`，等的是**专家 blob 的拷贝事件**；
>    且代码已有 `core::PinnedRing up_ring`（#1996）。R15 的"改 pinned"方向需重写。
> ④ §3.1 的"融合路径已经存在"**不成立**：`gemm_iq_f16_grouped` 只在 `pf_wmma()` 为真时可达，而 `pf_wmma()`
>    在 `__HIPCC__` 下 **恒 false**；且它处理 IQ 格式，生产是 native pack + Q4_K（`iq_dequant_gu_f16`）。
> ⑤ §5 第 3 序"MMQ 是否已在用"**已有答案**：当前构建 `STRATA_PREFILL_MMQ=OFF`、`mmq::built()` 是桩 false
>    （AUDIT16 P0-4）⇒ 没有在跑，且被 `CMakeLists:145` 的 `STRATA_ENABLE_HIP` 门挡住。
>    **真正该排第一的是打开这道门（R16）**，不是 dequant 的融合路径。
> ⑥ §2 的"每 token 贵 2.7 倍"应为 **2.5×**；"wait copy 7–14%"上限是 **12.7%（rep0）/15.5%（warm）**。

> 2026-10-31 23:37–23:42。`STRATA_PREFILL_TIMING=1`（引擎自带 21 个相位，不改源码），
> 三档 prompt 各 3 次，`read in` 墙钟与 GPU timeline 逐条对齐。

## 1 一句话结论

**dense FP16 GEMM 在短 prompt 里只占 0.68%（W851 的算术），而这里能看见的钱在别处：
MoE 专家 GEMM（gate/up + down）29–35%、专家反量化 `dequant` 8–20%、`wait copy` 7–14%。**

而且 **`dequant` 与 `wait copy` 是「几乎不随 token 缩放」的固定成本** —— 小 prompt 上它们占三分之一，
大 prompt 上被摊薄。这就是「短 prompt 每 token 贵 2.7 倍」的直接原因。

## 2 相位表（三档，中位那一次）

| 相位 | 277 tok | 1239 tok | 2323 tok | 性质 |
|---|---:|---:|---:|---|
| **gemm gate/up** | 222 ms (18.8%) | 557 (20.8%) | **830 (21.5%)** | 专家 GEMM，随 token 增 |
| **gemm down** | 156 (13.2%) | 359 (13.4%) | **523 (13.5%)** | 同上 |
| **dequant** | **217 (18.4%)** | 313 (11.7%) | 324 (8.4%) | **专家权重 Q4_K→FP16，几乎不随 token 变** |
| **wait copy** | **170 (14.4%)** | 415 (15.5%) | 259 (6.7%) | 主机拷贝等待（unpinned blob） |
| gdn | 76 (6.4%) | 220 (8.2%) | 420 (10.9%) | 随 token 增 |
| qsa attn | 11 (0.9%) | 106 (3.9%) | 311 (8.0%) | 长 prompt 才起量 |
| qsa proj | 32 (2.7%) | 92 (3.4%) | 168 (4.4%) | |
| hc read: down+silu | 48 (4.1%) | 76 (2.8%) | 143 (3.7%) | |
| hc read: up / inject / mix | 26/35/6 | 69/37/21 | 118/40/37 | 合计 ~7–10% |
| router+shared | 33 (2.8%) | 80 (3.0%) | 121 (3.1%) | |
| gdn out proj | 33 (2.8%) | 94 (3.5%) | 163 (4.2%) | |
| gdn recurrence | 16 (1.4%) | 72 (2.7%) | 132 (3.4%) | |
| host grouping | 34 (2.9%) | 73 (2.7%) | 119 (3.1%) | |
| combine | 28 (2.4%) | 26 (1.0%) | 33 (0.9%) | |
| hc write | 14 (1.2%) | 31 (1.2%) | 47 (1.2%) | |
| qsa indexer / select / gemms / norm | ≈0 | ≈0.3% | ≈0.8% | **indexer 恒为 0** |
| **host staging（另一行）** | 57 ms | 279 ms | **487 ms** | 随 token 增，2323 tok 时占 12.6% |
| **GPU timeline / wall** | 1180 / 1184 ms | 2682 / 2694 | 3863 / 3883 | wall ≈ GPU，说明**不是主机在等** |

三个 token 档的 `wall ≈ GPU timeline`（差值 4–20 ms），意思是：**GPU 是唯一瓶颈，主机不是。**
所以 `host staging` 那 487 ms 是**并行的**（GPU 在跑、主机在准备下一个 chunk），不额外拉长墙钟。

## 3 由此得到的三个可执行判断

### 3.1 `dequant` 是「固定成本」，小 prompt 上最值钱

专家权重从 Q4_K blob 反量化成 FP16，`kernels.cu:3117 blob_dequant` 写进 `DQ=2` 的 dequantized-expert ring。
绝对值：**217 ms（277 tok）→ 313（1239）→ 324（2323）** —— 基本不随 token 变。

⇒ 这是"每批专家反量化一次"的成本。**削它的收益全部落在短 prompt 上**：
277 tok 时它占 **18.4%**，削一半就是 −9% 的墙钟；而 2323 tok 时只有 8.4%，削一半 −4%。

源码里已经有两条相关线索：
- `gemm_iq_f16_grouped`（`prefill.cpp:1326`）：**每个 weight superblock 在 shared memory 里只反量化一次**，直接喂 FP16 路径 —— 融合路径已经存在；
- `STRATA_DEQUANT_SIDE=1`：另一块 scratch，把 dense 权重在 GEMM 前一次性反量化。

⇒ 下一步该问的是：**为什么 277 tok 还在走「独立 dequant 到 DQ ring」而不是融合路径？** 是阈值、是 ring 深度、还是专家命中情况决定的。

### 3.2 `wait copy` 14.4%:它是「等一块 unpinned blob 拷完」

`prefill.cpp:3456` 的注释写得很直白：

> behind a host copy of an unpinned blob (that wait left the GPU idle: the 'wait copy' / 'dequant' time of the ...)

⇒ 主机侧拷贝没走 pinned memory，GPU 只能等。这与 `X2 --ulimit memlock`（容器 `ulimit -l=8192KB`）
和 `STRATA_RESIDENT_PIN`（P71）是同一个根因家族 —— 之前判"收益 0"是因为只看了 `--ple-io`，
**没看这条 unpinned blob 的拷贝**。

这条比 hipFile 更容易：pinned 拷贝是标准手段，不依赖 ROCm 版本。

### 3.3 `qsa indexer` 恒 0 —— 一个可以关掉的假设

8 个样本里 `qsa indexer` 全是 0 ms（0.0%），`qsa select` 0.1–0.2%。
W839/W835 曾把「native_qsa_indexer 是否 tiled」列为探针（M4）—— 现在可以直接判：**它在这条路径上不耗时**，
不值得再查。

## 4 与既有记录的关系（要更新的旧结论）

| 旧记录 | 现在 |
|---|---|
| W804「1–3K 是 staging + CPU」 | **host staging 确实随 token 涨（57→487 ms），但它是并行的**（wall ≈ GPU timeline）。真正串行的是 `wait copy`（拷贝等待）与 `dequant` |
| P104「prefill 主战场 hc18 / GU16 / attn16 / gdn14 / gemmd9」 | 10.1 + 84 行表下：**GU 19–22% / down 13% / dequant 8–18% / wait copy 7–15% / gdn 6–11% / attn 1–8%**；hc 系列合计 ~10% |
| W851「dense GEMM 只占 0.68%」 | 成立，且解释了为什么补 256/512 桶看不见收益 —— 那 0.68% 里再省一半 = 0.34% |

## 5 下一枪（按性价比重排）

| 序 | 动作 | 为什么排这里 | 成本 |
|---|---|---|---|
| **1** | 查 `dequant` 为什么在短 prompt 走独立的 DQ ring 而不是融合路径，能否改成融合 | 固定成本、短 prompt 占 18.4%，且**已有融合 kernel**（不是从零写） | 读源码 + 1 次 A/B |
| **2** | `wait copy` 的 unpinned blob 改 pinned（或 `--ulimit memlock=-1` + `STRATA_RESIDENT_PIN`） | 14.4% 的纯等待，机制明确 | 改 compose + A/B |
| 3 | 专家 GEMM（GU+down 29–35%）—— MMQ 是否已在用、能否避免 FP16 反量化 | 最大单块，但要动 kernel | 大 |
| 4 | `qsa attn` 在长 prompt 占 8% —— 与 #3987（top-k split）同一条线 | 长 prompt 专项 | 中 |
| 5 | ~~qsa indexer~~ | **已判：恒 0，不做** | — |
