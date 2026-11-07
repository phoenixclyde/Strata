# W906 · ki 的 gfx906 内核：不能移植的理由不是"拿不到"，是"换了更差"

> 2026-11-03 02:4x。零停服、零落产。源码取自 `KIntegrated/vllm-gfx906-mobydick @3857591`（2026-10-26，
> 本地 `albus/w896/forks/ki-latest`）。本件回答：那批 gfx906 专用内核到底能不能用在我们身上、值多少。

---

## 1 它有什么（5,220 行，全部 gfx906 专用）

| 文件 | 行数 | 是什么 |
|---|---:|---|
| `csrc/rocm/dense_gemv_gfx906.cu` | 1,436 | M=1 W16A16 dense GEMV，每线程 16 B 沿 K，`__ockl_fdot2` |
| `csrc/rocm/moe_q_gemm_gfx906.cu` | 910 | **MoE W4A16 GEMM**（AWQ/GPTQ 打包），4 波/块、BLOCK_KN=256 |
| `csrc/rocm/moe_align_m1_gfx906.cu` | 173 | M=1 的专家行对齐/索引 |
| `csrc/gfx906_fa/kernel/fattn-q8.cuh` | 1,273 | decode/prefill FA（Q8 K + fp16 V） |
| `csrc/gfx906_fa/kernel/fattn-q8-paged.cuh` | 768 | 分页版 |

## 2 为什么"移植 MoE GEMM"这条路本身不成立

| 维度 | ki | 我们 | 后果 |
|---|---|---|---|
| 权重格式 | **W4A16 AWQ/GPTQ**：`int32 [E, K/8, N]` + exllama shuffle + fp16 scales + 打包零点 | **Q4_K**：144 B / 256 值，6-bit scales + min，llama.cpp 超块 | 移植＝**重打 77 GB 权重**，并丢掉与 llama.cpp MMQ 的兼容 |
| 计算指令 | `__ockl_fdot2` = `v_dot2_f32_f16`（**2 MAC/指令**），fp16 | `v_dot4_i32_i8` dp4a（**4 MAC/指令**），int8 | 同样 MAC 数，ki 要发 **2 倍指令** |
| 实测算术峰值 | 其日志自述 **~20 TFLOPS @930 MHz** | 我们实测 **19.07 TMAC/s = 38.1 TFLOPS-eq** | **ki 的上限只有我们的一半** |
| 在模型内实测 | **9.6 TFLOPS**（= 4.8 TMAC/s，"48% of dot peak"） | **9.1 TFLOPS**（= 4.55 TMAC/s，即 prefill 实测反推） | **绝对吞吐打平** |

⇒ **换过去不会更快**：算术上限减半，实际吞吐持平。这条要写死，避免以后又有人提"移植 ki 的 W4A16"。

## 3 但它记录了一个我们正在踩的坑（这才是真正可取的）

`DEVLOG-moe-gemm1-retiling.md`（2026-08-19，结论 DEAD-END）里的关键实测：

| 变体 | 块×波 | µs/launch | 对比 |
|---|---|---:|---|
| **current（256t，z=8 K-split + CAS）** | 64 × 4 | **26.9–27.1** | — |
| v1b（128t，NPT=1，**full-K**，直接写） | 64 × 2 | 60.4–60.5 | **2.2× 慢** |
| v1a（32t=半波，NPT=4，full-K） | 64 × ½ | 117.2–117.4 | **4.3× 慢** |

机制（原文）：「64 blocks each streaming one long 128 KB weight sequence **can't keep enough bytes in
flight** on the MI50（~128–512 KB in flight vs **~480 KB needed at ~300 GB/s × ~600 ns HBM latency**）」，
而「the current **8-way K-split keeps 64 independent 16 KB streams** turning over」。

**同一个日志还有两条我们这两天亲手验证过的同款结论**：
- 「in-model eager census 的 −186 µs/step **never appears in wall-clock** in either regime」→ 等于我们的 `W902`（微基准 3.14× → 真核 0%）；
- 「all retiling of the decode-size gemm1 is closed」→ 等于我们的 `W904`（tile/解包改法全负）。

## 4 我们的 MMQ 正好是它测出来更慢的那个形状

`mmq-config-gcn.cuh` 里 Q4_K 的每一行：

```c
CASE(GGML_TYPE_Q4_K, 256, 2,  64,   8, GGML_CUDA_MMQ_SRAM_LAYOUT_Q8_1, MMQ_ITER_K, false, true);
//                                                                         ...K_vram  stream_k ^^^^^  ^^^^^ fallback
```

**`stream_k = false`** ⇒ 走 `block_nums_xy_tiling` 的经典 tiled 发射，**每个块把整条 K（2560）走完**，
这正是 ki 测出来慢 2.2–4.3× 的 **full-K / 单条长流**形状。它的赢法是**把 K 切成 z=8 条独立流**，
让更多字节同时在飞。

⇒ 我们 prefill 只跑到 dp4a 实测峰值的 **24%**（4.55 / 19.07 TMAC/s），而 ki 用一半算术上限的指令
跑到自己峰值的 **48%**——**差的就是"并发权重流"这一层**，不是指令、不是解包（R51 已验证）。

## 5 可执行条目 R60（不是移植，是取它的机制）

**做法**：把 gcn 表里 Q4_K 的 `stream_k` 置 **true**（llama.cpp 自带 stream-k + fixup kernel，
`mmq.cuh:1477-1500`），只重编 `mmq-instance-q4_k.cu` 一个 TU（`W904 §7.1` 的换对象重链通路，已验证 6 分钟出二进制）。

**为什么值得**：等价的 K 切分在 ki 上是 **2.2×**（26.9 vs 60.4 µs）；我们的 `stream-k` fixup 是确定性累加，
不需要它那套 CAS 原子。

**两条必须先说清的风险**：
1. **会改求和序**（部分和按不同顺序相加）⇒ **不是逐位相同**，必须过 `R59` 的 KL/top-1 门
   （判据 KL ≤ 0.005 且 top-1 ≥ 99%）。这正好是 R59 的第一个应用场景。
2. AMD 上 stream-k 的网格被写死为 `nsm`（`mmq.cuh:1478`：`GGML_CUDA_CC_IS_NVIDIA(cc) && eff>=90 ? ntiles : nsm`）
   ⇒ gfx906 上是 **60 块 = 1 块/CU**。若打开后反而变慢，第一条要试的是把那个 NVIDIA 条件放开到 HIP。

**判据**：prefill TTFT 中位 `|Δ| ≥ 2×CV`（服务端 `prompt ... read in` 口径）+ R59 的精度门；decode 只守不劣化。

## 6 一句话

ki 的 gfx906 内核**不是我们不能移植，是移植了更慢**（算术上限减半、实测打平、还要重打 77 GB）。
真正值钱的是它用 µs 级实验证明的那条机制——**K 方向要切成多条独立流**——而我们自己的 Q4_K 配置
恰好是 `stream_k=false`（full-K），所以 R60 是"借它的结论改我们的一行配置"，不是"搬它的代码"。
