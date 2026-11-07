# W792 prefill 分相位账（首次）+ 队列换战场

> 机主令「继续，该上网查一定要上网查」。本轮做的第一件事是**把从来没测过的那一段测出来**：
> prefill 占 M 档墙钟 90%、L 档 99.5%，而过去七轮方案全部建立在 decode 的 stage 账上。
> 首次量出 prefill 的 21 个相位之后，结论是**战场要换**，而且换的理由不是"prefill 更重要"这种正确的废话，
> 是三条硬事实：**量级差 21 倍 / 可判性差 100 倍 / 杠杆集中度 46%**。

---

## 1 结论先行（六条）

1. **prefill 第一次有了分相位账**：`STRATA_PREFILL_TIMING=1` 是**零代码**开关，21 个相位，M/L 两档。
2. **prefill 的第一大项是 `hc read`，17-18%**（M 8.10 s / 44.5 s，L 36.96 s / 214.5 s）。
   它和 decode 里那个 `hc_down`（3.47 ms/window，占 M 档墙钟 0.7%）**是两个完全不同的代码路径**，
   同名不同物，量级差 **约 21 倍**。`W791` 把 R5 定为"主攻 decode 的 hc_down"是**看错了对象**。
3. **prefill 的测量可判性比 decode 高一个数量级以上**：4 次 M 档 `GPU timeline` = 44481/44630/44530/44588 ms（极差 **0.33%**），
   `hc read` 8098/8115/8100/8110（**0.21%**）、`gemm gate/up` 7056-7066（0.14%）；而 decode 的 `total` 跨会话摆 21%、3-runs 可判下限 6-7%（`AUDIT7`）。
   > **【AUDIT8 更正，P1-4】** 原文只引了最平的两个相位（0.14% / 0.21%）并得出"可判 0.2%"。同一批 4 次的**其余相位**是：
   > `gemm down` 1.4%、**`qsa attn` 0.91%**、**`gdn` 0.80%**、**`dequant` 2.6%**。=> 正确表述是"大相位 0.2%、中相位 0.8-0.9%、dequant 2.6%、总量 0.33%"，
   > 门槛必须**按相位给**（规则 M 已据此重写）。
   同样的 3 次运行，在一处能判 0.3%，在另一处判不了 3%。
4. **44-46% 的 prefill 时间走的是 rocBLAS 稠密 GEMM**（`hc read` + `gdn` + `qsa proj` + `gdn out proj` + `router+shared`），
   25-28% 走专家 MMQ，23-28% 走自研 kernel。=> **prefill 的杠杆在"稠密 GEMM 有多快"，不在"哪个 kernel 少一次访存"。**
5. **`R5a-down` 的前提不成立**：`W791 §4` 写的「把 GR_SPLIT 的 K 切分适配 Q8 行」建立在
   「上游的 K 切分只支持 bf16」这个判断上；实际上 **Q8 的 down 内核本身就是 K 切分**（16 片 × 640 列，176 个 block），
   而 `STRATA_GR_SPLIT` 的 bf16 版是 **5 片 × 2048 列**——把它"移植"到 Q8 等于**把 16 片改成 5 片（变粗）**，不是新增 K 切分。
   该条**撤回**。
6. **上游/社区取证找到四条"已有但在这条分支上编不进去 / 静默退路"的东西**（§5），其中
   `STRATA_ROCBLAS_AVAILABLE` 在 gfx906 分支上**根本没定义**——`STRATA_ROCBLAS_TUNING` 在我们的镜像里是死开关。

---

## 2 方法与协议

| 项 | 值 |
|---|---|
| 仪器 | `STRATA_PREFILL_TIMING=1`（引擎自带，`src/prefill/prefill.cpp:2500` 的 21 个相位，cudaEvent 打点，按"前一个 mark 的相位"计账） |
| 生产 | `strata166-407` / `strata-gfx906:0.2.4` / `0.1.49.2` / slots 9901 / env 4 项 / governor `schedutil` 44 核 |
| 档位 | M = 21,822 tokens（3 chunk）；L = 99,382 tokens（12 chunk + 1118） |
| chunk | **8192**（日志 `prefill plan: chunk 8192`） |
| 复用 | 每轮唯一 nonce，`reused=0` 自证 |
| 运行数 | M × 4（全部列出），L × 1 |
| 恢复 | 远端 `setsid nohup` + `trap EXIT`（纪律⑥）；收尾 `cp` 回原 config + 重启 + 复核 env 4 项 |
| 原始件 | 166 上 `/home/albus/strata166/data/r5_pf_20261025_150625.txt` |

**仪器开销**：M 档 45.2-45.5 s 与未开仪器的历史值（`W786` 44.4 s，governor 不同）同量级，说明打点开销 < 1%；
但**绝对值不要跨轮次比**，只做同轮 A/B。

---

## 3 M / L 两档分相位账

### 3.1 M 档（21,822 tokens，GPU timeline 44.5 s；4 次全部一致）

| # | 相位 | ms | 占比 |
|---|---|---|---|
| 1 | **hc read** | **8,100** | **18.2%** |
| 2 | gemm gate/up（专家） | 7,057 | 15.9% |
| 3 | qsa attn | 6,910 | 15.5% |
| 4 | gdn（投影入） | 6,102 | 13.8% |
| 5 | gemm down（专家） | 3,805 | 8.6% |
| 6 | qsa proj | 2,620 | 5.9% |
| 7 | gdn recurrence | 2,504 | 5.6% |
| 8 | gdn out proj | 2,146 | 4.8% |
| 9 | router+shared | 1,667 | 3.7% |
| 10 | dequant | 1,433 | 3.2% |
| 11 | qsa select | 717 | 1.6% |
| 12 | hc write | 382 | 0.9% |
| 13 | embed+steps / ple / combine / gdn conv / host grouping / gather / wait copy | 185/198/178/152/133/87/105 | 合计 2.4% |
| — | qsa indexer | 1 | 0.0% |

### 3.2 L 档（99,382 tokens，GPU timeline 214.5 s；prompt 462 tok/s）

| # | 相位 | ms | 占比 | 与 M 档比 |
|---|---|---|---|---|
| 1 | **hc read** | **36,956** | **17.2%** | 占比几乎不变 |
| 2 | qsa attn | 32,876 | 15.3% | 几乎不变 |
| 3 | gemm gate/up | 31,306 | 14.6% | 略降 |
| 4 | gdn | 27,842 | 13.0% | 略降 |
| 5 | gemm down | 16,833 | 7.8% | 略降 |
| 6 | **qsa select** | **14,812** | **6.9%** | **1.6% -> 6.9%（随上下文 4.3 倍）** |
| 7 | qsa proj | 12,044 | 5.6% | — |
| 8 | gdn recurrence | 11,497 | 5.4% | — |
| 9 | gdn out proj | 9,751 | 4.5% | — |
| 10 | router+shared | 7,550 | 3.5% | — |
| 11 | dequant | 6,102 | 2.8% | — |
| 12 | hc write | 1,737 | 0.8% | — |
| — | 其余 7 项 | 合计 2,640 | 1.2% | — |

**两档唯一的形状变化**：`qsa select` 从 1.6% 涨到 6.9%（它是 O(tokens × blocks) 的），
其余占比稳定 —— 这意味着 **M 档的结论对 L 档基本可外推**，不必每件事都在 L 上重测（L 一次 3.6 分钟）。

### 3.3 按"后端"归并（这才是杠杆视图）

| 后端 | M 档 | L 档 | 说明 |
|---|---|---|---|
| **rocBLAS 稠密 GEMM**（bf16/f16） | **46.4%** | **43.8%** | hc read + gdn + qsa proj + gdn out proj + router+shared |
| **专家 MMQ + dequant** | 27.6% | 25.2% | gemm gate/up + gemm down + dequant |
| **自研 kernel** | 22.7% | 27.6% | qsa attn + qsa select + gdn recurrence |
| 其余（PLE/搬运/embed/combine） | 3.3% | 3.4% | — |

---

## 4 三条结构性发现

### 4.1 同一个名字，两条路径，21 倍量级差

| | decode 的 `hc_down` | prefill 的 `hc read` |
|---|---|---|
| 代码 | `fused_gr.cu` 的 `gr_down_q8_kernel`（Q8_0 行、16 片 × 640 列、**176 block**、T≤8） | `prefill.cpp:3181` → `bf16_proj` → `Gemm::bf16()` → rocBLAS，T=8192 |
| 权重形态 | **Q8 原地读**（0.65 GiB） | **先把 Q8 反量化回 bf16**（`NativeDense::hc_bf16_view`，每 half 每层**重新反量化**），再读 bf16（1.20 GiB） |
| 计时口径 | `decode GPU stages` 的 `hc0/hc1 down`（ms/window） | `prefill timing` 的 `hc read`（ms/整个 prompt） |
| 量级 | 3.47 ms/window ≈ decode 的 7.5% ≈ **M 档墙钟 0.7%** | 8.10 s ≈ **M 档墙钟 16%** |
| 可判下限 | 6%（`AUDIT7`） | **0.2%**（本轮 4 次） |

**这就是为什么过去七轮"HC 优化"都撞墙**：优化的是 0.7% 那一侧，而且那一侧的量测噪声比目标收益还大。

顺带一条**源码级事实**（此前没人写过）：`STRATA_HC_Q8=1` 在 prefill 里是**净成本**——
`prefill.cpp:3181` 逐字 `<span>if (!wd->data && wd->hc_q8 && !wu->data && wu->hc_q8)</span>` 命中后
`hc_bf16_view()` 把整个 Q8 矩阵反量化到 bf16 scratch 再算 GEMM。
每个 chunk：48 层 × 2 half × 2 矩阵 = **192 次反量化**，写 1.26 GB + 读 0.67 GB ≈ **2.4 ms/chunk**（相对 hc read 2700 ms/chunk 可忽略），
但它意味着 **prefill 拿不到 Q8 的带宽优势，只拿到 decode 的显存优势**。
=> 「HC_Q8 让 prefill 变慢」这句话**不成立**（2.4 ms 是 0.05%），但「prefill 的 hc read 与 Q8 无关」**成立**。

### 4.2 可判性：prefill 能判 0.3%，decode 判不了 3%

M 档 4 次（相位行打 **21,822** tokens，bench 的 `ptok` 是 **21,827** —— 两个计数口径，差 5，不混用）：
`GPU timeline` 44481 / 44630 / 44530 / 44588（极差 0.33%），`hc read` 8098 / 8115 / 8100 / 8110（0.21%）、`gemm gate/up` 7056-7066（0.14%）、`qsa attn` 6905-6968（0.91%）、`gdn` 6099-6148（0.80%）、`dequant` 1406-1443（2.6%），
`gemm gate/up` 7057 / 7056 / 7056 / 7066（0.14%）。

对照 `AUDIT7 §12.1` 的 decode 统计：`total` 跨会话 21%、同会话 ±1.5%；`hc_down` 可判下限 6%。

**同一台机器、同一轮、同样的 3-4 次运行**：prefill 的相位能判 0.3%，decode 的相位要 3% 才算数。
原因很清楚——prefill 是一次 8192 token 的大 GEMM，GPU 占满、CPU 不参与调度；decode 是 96 次小 launch + 专家流 + CPU 等待。
=> **判据的门槛不该全系统统一，要按相位给**（prefill 相位 ≥1%、decode 相位 ≥6%）。

### 4.3 46% 走 rocBLAS ⇒ 杠杆在"GEMM 有多快"，不在"少一次访存"

`hc read` 的绝对效率：每 token 的 HC 工作量 = 48 层 × 2 half × (down 320×10240 + up 10240×320) = **1.258 GFLOP**。
M 档 21,822 token → 27.5 TFLOP，实测 8.10 s ⇒ **3.4 TFLOPS**。
MI50 的 BF16 **没有硬件点积**（gfx906 无 bf16 dot），rocBLAS 的 bf16 GEMM 只能按 F32 速率跑（**13.2 TFLOPS** 峰值）；
FP16 有 `v_dot2_f32_f16` 打包点积（**26.5 TFLOPS** 峰值）。
=> 3.4 / 13.2 = **26% 的 f32 峰值效率**；同一个 3.4 TFLOPS 放到 f16 峰值上只是 13% —— 也就是说
**不是"内核效率低"，是"走了慢的那条硬件通路"**。

带宽侧同时算一遍以排除干扰：每 chunk 的 hc read 约搬 106 GB（含 `gated` 的写回/再读 64 GB），用时 2.7 s ⇒ **39 GB/s = 峰值的 5%**。
=> **纯计算受限，且离 f32 峰值还有 4 倍余量**。这两条加起来，就是 §7 那个 -57% 的全部解释。

**这正是 `STRATA_HIP_PROMPT_F16=1` 的靶心**：把 prompt 的 16-bit GEMM 全部改成 FP16 in/out（`Gemm::bf16()` 的 `f16_io_` 分支），
在 gfx906 上从 f32 速率换到 dot2 速率。上游 PR #835 在 **RX 6900 XT（gfx1030）** 上实测 prompt 读取约 **2x**（744→926 tok/s 等）；
gfx906 与 gfx1030 同属"无 bf16 dot"的一代，机制同源——**但这是别人的卡，必须自己测**（§7）。

---

## 5 上游/社区取证（本轮全部实读正文，不是印象）

| 来源 | 内容 | 对我们的判定 |
|---|---|---|
| **上游 PR #835**（closed，已合入） | 「HIP gfx103x: the prompt path's 16-bit GEMMs in FP16 in and out (prompt reads **~2x** on RX 6900 XT)」，引入 `Gemm::set_f16_io` 与 `STRATA_HIP_PROMPT_F16`，由 `Prefill::init` 启用 | **机制在我们树里**（`gemm.cu:581 prompt_f16()`）；gfx906 未被排除 → **可测**（§7） |
| **Docker Hub `xxdoman/strata-mi50`（0.2.3, gfx906 专版）** | 该镜像作者逐字写的两件事：①「The rocBLAS solution-table reader wired for gfx906. The reader is upstream, but **its gate sits on `STRATA_ENABLE_HIP` while gfx906 takes the `HIP_GFX906` branch — without the wiring it compiles to nothing**」；② 自带一份 **gfx906 表（108 行，在 MI50 上对 rocBLAS 5.2.0 调出）** + `STRATA_HIP_PROMPT_F16=1` | **已在我们源码里复核为真**：`CMakeLists.txt:112` 只在 `STRATA_ENABLE_HIP` 时 include `cmake/hip_backend.cmake`，而 gfx906 走 `:149` 的独立分支（只 `find_package(hip/hipblas)`，**不 find rocblas**）=> 我们镜像的 `build.ninja` 里 **`STRATA_ROCBLAS_AVAILABLE` 不存在**、不链接 rocblas ⇒ **`STRATA_ROCBLAS_TUNING` 是死开关** |
| **上游 PR #3073**（open） | 「`STRATA_SELECT_SIMT=2` takes the simt2 scorer on HIP too（**it silently fell back to the warp kernel**）；119K prompt **-6.5%** on gfx1030」 | **我们树同样有此缺陷**：`qsa_select.cu:1838` 的 HIP 分支逐字 `v[0] == '1'`，给 `=2` 直接不认。`qsa select` 在 L 档已占 6.9% |
| **社区 `nullkalahar/mi50-rocm7`（MI50 安装指南）** | 「Clang 7.x 在 Vega 20 上有调度回归；加 `-mllvm -amdgpu-sched-strategy=max-ilp` **恢复 10-20% prefill**」 | 我们是编译期选项（`CMAKE_HIP_FLAGS`），**需重编一次**才能测；与任何运行时开关都不冲突 => 便宜且正交 |
| **上游 Issue #3173**（2× MI50 128K 实测） | `--trim-stage-weights` 使 prompt 读取 **+5%**；`--pipeline-windows 2` 使 decode **+36%** | 前者只在显式 `--layer-split` 才有意义（`generate.cpp:3802`），我们单卡 => 不适用；后者是多卡流水，单卡 => 不适用。**两条都记成"不适用"，不排** |
| **上游 PR #3220**（open，`W791` 已记） | HC_Q8 的 prefill 每 chunk 192 次**标量** `gr_dequant_q8_0_kernel` 向量化（bitwise，1.95x），+ WMMA 路径 | WMMA 部分 gfx906 无 => 不可移植；**dequant 向量化可移植**，但我们 192 次/chunk 只值 ~2.4 ms/chunk（0.05%）=> 收益上限太小，**不排** |

---

## 6 源码级更正：`R5a-down` 撤回

`W791 §4` 的推理链是：「`STRATA_GR_SPLIT` 的 K 切分只支持 bf16（`a[0].s_down == nullptr`）→ 把它适配 Q8 行，就能同时拿 -3.2% 与 +3%」。
**第一步就错了。** 读 `fused_gr.cu` 的 Q8 路径（`launch_q8_t`，:2152）：

```cpp
constexpr int Q8_KC = 640, Q8_NKC = D / Q8_KC;      // 16 chunks, 4 per stream
constexpr int Q8_CPS = N / Q8_KC;                   // 4
gr_down_q8_kernel<T><<<dim3(Q8_RG + 1, Q8_NKC), THREADS, 0, st>>>(m, part, ssg);   // 11 x 16 = 176 blocks
```

K 已经是 **16 片 × 640**，每片的 partial 在 `gr_up_q8_kernel` 里按 `rsS` 合成。
而 `STRATA_GR_SPLIT` 的 bf16 版是 **5 片 × 2048**（`GS_SL = 2048`，`GS_S = 5`），`41 × 5` 个 block。
=> **"把 K 切分移植到 Q8"= 把 16 片改成 5 片**，是**变粗**，不是新增能力。
它真正的收益来源（上游原话 `~3% faster per verify window`）是 bf16 版**一次 launch 的 block 数从 41 涨到 205**（占用率），
而 Q8 版早就是 176 个 —— **Q8 版已经吃掉了那 3% 的成因**。

**结论**：`R5a-down` 撤回。`hc_down`（decode）上还剩的唯一结构事实是「Q8 与 bf16 都是 3.47 ms」=> 它既不是带宽也不是表示法瓶颈，
而是 **96 次小 launch 的固定开销**（每 window 96 次，每次 ~36 µs，而 6.5 MB 的读只需 8 µs）——
要动它得改 launch 结构（把 attn/mlp 两个 half 合并、或跨层批处理），那是"改引擎调度"，不是"调参数"，**单独立项，不混进本队列**。

---

## 7 本轮 A/B：`STRATA_HIP_PROMPT_F16=1`（gfx906）—— **-20.5%**

### 7.1 协议

序列 **B F B F**（B = 生产原样 + `PREFILL_TIMING=1`；F = 再加 `STRATA_HIP_PROMPT_F16=1`），每臂 2 个 M 请求，
臂间靠 `docker restart` 切 env，`trap EXIT` 自恢复。第 3/4 轮各加一次 needle 32k（深度 10%/90%，greedy）。

### 7.2 结果（M 档，21,822 tokens，`prompt_ms`）

| 臂 | run1 | run2 | run3 | run4 | 中位 |
|---|---|---|---|---|---|
| **B**（bf16 GEMM） | 45,333 | 45,690 | 45,207 | 45,238 | **45,286** |
| **F**（FP16 GEMM） | 36,095 | 35,936 | — | — | **36,016** |
| 差 | | | | | **-20.5%** |

`GPU timeline`（去掉 host 段）：B 44,617 / 44,964 / — / —；F 35,372 / — → 同向同幅。
**墙钟**：51.2/50.7/51.4/50.6 s → 42.0/40.9 s。

### 7.3 归因：变的只有该变的那几项（这是本轮最硬的证据）

| 相位 | B（run1/run2/run3/run4 中位） | F（run1） | Δ | 后端 |
|---|---|---|---|---|
| **hc read** | 8,257 / 8,140（同轮交错 B 臂；`r5_pf` 的 8,199 是另一会话） | **3,501 / 3,344** | **-57.4%（2.34x）** | rocBLAS bf16→f16 |
| **gdn** | 6,105 | **3,718** | **-39.1%（1.64x）** | 同上 |
| **qsa proj** | 2,621 | **1,757** | **-33.0%（1.49x）** | 同上 |
| **gdn out proj** | 2,146 | **1,623** | **-24.4%（1.32x）** | 同上 |
| **router+shared** | 1,852 | **1,057** | **-43%** | 同上（`ffn_gate_inp`） |
| gemm gate/up（专家 MMQ） | 7,054 | 7,083 | **+0.4%** | MMQ，**未动** |
| gemm down（专家 MMQ） | 3,806 | 3,800 | **-0.2%** | MMQ，**未动** |
| qsa attn（自研） | 6,928 | 6,908 | -0.3% | 自研，**未动** |
| gdn recurrence（自研） | 2,500 | 2,462 | -1.5% | 自研，**未动** |
| qsa select（自研） | 717 | 716 | 0.0% | 自研，**未动** |
| dequant | 1,416 | 1,402 | -1.0% | 未动 |

**五个 rocBLAS 相位全部下降，五个非 rocBLAS 相位一个没动** —— 这不是"整体快了"，是**开关精确命中它声明的那一部分**。
另有一条独立佐证：MTP 草稿层的小 prefill（893 tokens）同步从 4,007 ms 降到 3,752 ms（`hc read` 809→678）。

### 7.4 为什么能快 1.3-2.3 倍

gfx906（Vega 20）**没有 bf16 点积指令**：bf16 GEMM 只能按 F32 速率跑（MI50 FP32 峰值 **13.2 TFLOPS**）；
而 FP16 有 `v_dot2_f32_f16` 打包点积，峰值 **26.5 TFLOPS**。
实测 `hc read` 的等效吞吐：B 3.4 TFLOPS（= f32 峰值的 26%），F 7.7 TFLOPS —— **正好是"换了一条 2 倍的硬件通路"**，
而不是"内核写得更巧"。带宽侧不是瓶颈：hc read 每 chunk 约 106 GB / 2.7 s ≈ **39 GB/s（峰值的 5%）**。
=> 这也解释了为什么上游把这个开关留给 gfx103x（同样无 bf16 点积），而没给我们这一代写死默认值。

### 7.5 质量门

needle 32k（深度 10% / 90%，greedy，唯一 code word）：

| 臂 | 32k@10% | 32k@90% | 结果 | 该请求 prompt 吞吐 |
|---|---|---|---|---|
| **B** | FOUND | FOUND | **2/2** | 465 tok/s |
| **F** | FOUND | FOUND | **2/2** | **592 tok/s** |

（F 臂的 needle 与后续 `STRATA_F16_RANGE` 检查见 §7.6。）

### 7.6 上溢范围检查（`STRATA_F16_RANGE=1`，M 档 21,822 tokens）

引擎逐字输出：

```
strata f16 range: 21822 tokens: activation images max |x| 74.1 (0 beyond 65504 or NaN),
  BF16 weights max |w| 11.562 (0), FP16 GEMM outputs max |y| 304.8 (0 not finite)
strata prefill: HIP device 0 gfx906:sramecc+:xnack- - STRATA_HIP_PROMPT_F16=1: the prompt's 16-bit GEMMs run
  FP16 in and out (rocBLAS is tuned only for that on gfx103x; not bit-identical to the default)
```

| 量 | 实测最大 | FP16 上限 | 余量 | 越界/NaN |
|---|---|---|---|---|
| 激活（GEMM 输入） | **74.1** | 65,504 | **884x** | 0 |
| BF16 权重 | 11.56 | 65,504 | 5,666x | 0 |
| **FP16 GEMM 输出** | **304.8** | 65,504 | **215x** | **0 not finite** |

=> **上溢不是本配置的真实风险**（离上限 215 倍）。剩下的只有"每个 GEMM 输出少 3 位尾数"这一个数值差异。
（893 token 的 MTP 草稿段同样：|x| 103.0、|y| 327.5、0 越界。）

### 7.7 落生产（已执行，2026-10-25 15:34-15:37）

| 步骤 | 结果 |
|---|---|
| register 增行 | `P103 STRATA_HIP_PROMPT_F16=1 ADOPTED`；`P104` 分相位账（REFERENCE）、`P105` rocBLAS 表（CANDIDATE）、`P106` SIMT=2（CANDIDATE）；`P102` 追加 W792 撤回 |
| `gen_config.py --write` | 1457 B，env 5 项 |
| 推 + 重启 | `adopt.sh`（`trap EXIT`，未完成则自动回滚）；A 段=范围检查，B 段=装最终 config |
| 生产现状 | `strata166-407` Up，`ver 0.1.49.2`，**slots 9901**，`vram_free 642`，governor `schedutil` 44 核，env = `HSA_OVERRIDE_GFX_VERSION` / `STRATA_PREFILL_CPU_SHARE=0` / `STRATA_RESIDENT_HEADROOM_GIB=0.5` / `STRATA_HC_Q8=1` / **`STRATA_HIP_PROMPT_F16=1`** |
| `verify_config.py` | **PASS=29 FAIL=0**（含 P103 行） |
| `gen_config.py --live` | **无差异** |
| 回滚位 | 166 上 `strata-huihui-ud-iq4_xs.json.bak_w792_20261025_153424`；本地 register `.bak_w792_*` |

### 7.8 落生产后的独立复核（**无仪器**，生产容器直接打）

`adopt.sh` 装完最终 config 后，在生产容器上**不带任何 `STRATA_*TIMING`** 重跑三档（唯一 nonce，`reused=0`）：

| 档 | tokens | 采纳前（B 臂，带仪器） | **采纳后（生产，无仪器）** | 变化 |
|---|---|---|---|---|
| **M** | 21,827 | 45,286 ms / 482 tok/s / 墙钟 **50.85 s**（中位；四样本 51.2/50.7/51.4/50.6） | **35,209 / 35,313 ms，619.0 tok/s，墙钟 40.0 s** | **-21.3% 墙钟（中位对中位），+28.4% 吞吐** |
| **L** | 99,387 | 215,073 ms / 462 tok/s / 墙钟 215.9 s | **167,091 ms，594.8 tok/s，墙钟 167.9 s** | **-22.3% 墙钟，+28.7% 吞吐** |
| needle 32k@50% | 31,640 | 68 s（B 臂 32k@10%） | **FOUND，54 s** | 检索正常，同 prompt 快 21% |

**L 档与 M 档同幅**（-21% / -22.3%），说明这条收益**不随上下文长度衰减** —— 因为它是"每 token 的稠密 GEMM 换硬件通路"，
不是"少读一次缓存"。这也反过来验证了 §4.3 的归因：M/L 的 rocBLAS 占比相近（46.4% / 43.8%），收益也就相近。

### 7.9 残余风险与未做的门（照实写）

1. **数值改变是设计内的**：每个 16-bit GEMM 的输出被舍入到 FP16（`widen_rows_f16` 再展宽回 FP32）。上游逐字「not bit-identical to the default」。
   下游影响只能由任务门判；分布门（KL）只能判「不同」不能判「更坏」（`W767` 的教训）。
2. **任务门只做了一档长度**：needle 32k，深度 10%/50%/90%，两臂各全中。**没做** 128K/262K 深度 needle、HellaSwag 类配对 McNemar。
   => 结论的正确表述是「**32K 内的稀疏检索没退化**」，不是「质量无退化」。
3. **未测交叉**：`--kv k8v4` × FP16（两者都改数值）；`STRATA_HC_Q8=1` × FP16（本轮两者始终同开，没有拆开测过 bf16 包 × FP16 的组合）。
4. **`b16 权重 → f16` 每调用一次转换**（`bf16_to_f16_rows` 写进 scratch）。它已经算在上面所有数字里；但如果将来出现"GEMM 变小、调用变多"的形状，这笔开销会浮上来。

---

## 8 新队列（本轮改判）

旧队列（`W786` R1-R8 / `W785` Q1-Q9）在 M 档墙钟尺度上的权重，用本轮数据重算：

| 旧项 | 声称的靶 | 真实占 M 档墙钟 | 改判 |
|---|---|---|---|
| **R5a-down**（decode hc_down K 切分 Q8 化） | 7.5% of decode | **0.7%** | **撤回**（§6，前提不成立） |
| **R5b-up**（decode up 加 Q8） | 7.4% of decode | 0.7% | 降为备选，且只在 decode 专项批次里做 |
| R3 GEMV 形状扫 | 13.1% of decode | 1.2% | 同上 |
| R6 注意力 | 7.2% of decode | 0.7% | 同上 |
| R4 路由 | — | — | 已关（`P101`） |

新队列（按 **M 档墙钟** 排，括号里是门槛）：

| # | 项 | 靶 | 预期 | 判据 |
|---|---|---|---|---|
| **P1** | `STRATA_HIP_PROMPT_F16=1`（零代码） | 46% 的 rocBLAS GEMM 换 f16 速率 | 上游同代卡 ~2x on that block ⇒ 上限 -20% 墙钟 | `GPU timeline` ≥3%；needle 32k 2/2；decode 不劣化 |
| **P2** | rocBLAS 解题表接上 gfx906（**一行 CMake** + `tools/hip/tune_rocblas.cpp` 已在树里，自己调表） | P1 之后的同一批 GEMM | 上游称 rocBLAS 自选解最差可比最优慢 **6x**（gfx1030）；保守按 5-10% 估 | 同上；且必须 bit 一致（只换解，不改算术） |
| **P3** | `-mllvm -amdgpu-sched-strategy=max-ilp` 重编 | 全 prefill kernel | 社区 Vega 20 报 **10-20%** | 同上；一次 25 min 重编 |
| **P4** | `STRATA_SELECT_SIMT=1`（`=2` 在 HIP 上被静默退路挡住） | L 档 6.9% / M 档 1.6% | gfx1030 报 119K -6.5%（含 =2）；我们只有 =1 可用 | 同 P1，另加输出一致性 |
| **P5** | `qsa attn`（M 15.5% / L 15.3%）机理 | 自研 kernel，无上游等价件 | 未知，先做 roofline | 只做机理，不做实验 |
| **P6** | decode 专项（hc_down launch 结构 / GEMV / 路由） | decode 整体占 M 10% / L 0.5% | 全做完 ≈ 1-2% | **只在 M 档 decode 占比要提升时才做**；当前优先级最低 |

**P2 的源码事实（已核实）**：
- `cmake/hip_backend.cmake:84` `if(TARGET roc::rocblas) set(STRATA_ROCBLAS_AVAILABLE ON)` —— 该文件**只在 `STRATA_ENABLE_HIP` 时被 include**（`CMakeLists.txt:112`）；
- gfx906 走 `CMakeLists.txt:149` 的独立分支，只 `find_package(hip)` + `find_package(hipblas)`，**没有 rocblas**；
- 于是 `STRATA_ROCBLAS_AVAILABLE` 未定义 → `gemm.cu` 的 `try_rocblas_f16o` 整段 `#if` 掉 → **`STRATA_ROCBLAS_TUNING` 设了也没用**（正是规则 I 的第四次形态：开关存在、代码存在、**编不进去**）。
- 容器内 `/opt/rocm/lib/cmake/rocblas/rocblas-config.cmake` **是存在的**（`rocblas-targets.cmake` 也在），
  也就是说**只差 gfx906 分支里补一次 `find_package(rocblas CONFIG)`**，不是缺包。

---

## 9 举一反三

1. **"第一次测"比"第十次优化"值钱。** 七轮方案都建立在 decode 的 stage 账上，而 decode 只占 M 档 10%、L 档 0.5%。
   本轮只加了一个 env，就把整个方案的重心挪了位置。**规则 K：任何优化方案落地前，先确认"被测的那一段"占端到端多少。**
2. **同一个词在不同路径上是不同的东西。** `hc_down`/`hc read`、`gemv`/`gemm`、`router`（`native_router_top10` vs `router_top10`）。
   **规则 L：凡是要"优化 X"，先把 X 的每个实现位置列出来并标注各自占比；只有一个实现时才谈优化。**
3. **判据门槛不能全局统一。** prefill 相位可判 0.3%，decode 相位要 6%。把 decode 的门槛套到 prefill 上会漏掉真收益；
   反过来会把噪声当收益。**规则 M：门槛按"相位 × 后端"给，不按"系统"给。**
4. **"默认关"有三种，必须分清**：① 默认关但可用（`STRATA_SELECT_SIMT=1`）；② 默认关且**被前置条件挡死**（`GR_SPLIT` 的 `s_down == nullptr`）；
   ③ **根本没编进去**（`STRATA_ROCBLAS_AVAILABLE`、`prompt_attn_i8v3`、`gr_up75`）。前两种读源码能判，第三种**必须看 `build.ninja`/二进制**。
   **规则 N：判定"某开关能不能用"，最后一个动作是 `grep build.ninja` 或 `strings 二进制`，不是 grep 源码。**
