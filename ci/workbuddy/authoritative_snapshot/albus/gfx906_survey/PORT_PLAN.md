# Strata × gfx906 专用优化移植方案（含 k8v4 / int8）

> 2026-11-07 05:1x 出具，05:3x 修订（**版本差已消除**：机主确认生产与分支同为 **0.1.57**）。
> 基于**自有分支源码** `phoenixclyde/Strata @ gfx906/mi50`（`CMakeLists.txt:11` = **0.1.57**），
> 因此下文所有 `文件:行` **就是产线行号**，落地时不需要重新定位。
> 注：本地 `deploy/SESSION_STATE.md:11` 与 `PARAM_REGISTER.tsv` P262/P263 仍写 `0.1.55w / /src=0.1.56`，
> 属陈旧行，本轮结束时应当回写（不改代码，只改记录）。
> 生产未改动、零停服。

---

## 0 结论

| 问题 | 回答 |
|---|---|
| **项目找全了吗？** | **没有。** 上一版清单只覆盖 KI（vLLM）+ llama.cpp + llama.cpp fork，**整整漏掉 Strata 自己的 gfx906 生态**（9 个仓库，含一份"port overlay"、一份 17 条负面结果台账、一份 query-swizzle 的正式实测）。本轮补齐 12 个仓库，见 §2。 |
| **Strata 缺的是什么？** | 不是"没有 gfx906 支持"——0.1.57 已有 **gfx906 默认表（2 项 bitwise）+ 7 项 tuned 包 + 一整套 int8/q4 KV 与 dp4a MMVQ**。缺的是**三处 dp4a 真空**：`fused_gr.cu` 的 HC 点积、`qsa_pattn.cu` 的 prefill 分数、`qsa_decode_attn.cu` 的 decode 分数。这三处都是"int8 码 → 逐元素反量化 → fp32 FMA"，而硬件有 `v_dot4_i32_i8`。 |
| **最值钱的一条** | **prefill 分数相位换 dp4a**（`qsa_pattn.cu:141-172`）。attn 占 prompt 16%（P104），分数相位每 cell 每 head 是 256 FMA + 256 反量化，dp4a 后是 64 条指令 ⇒ **同相位 ALU 降约 4×**。这是唯一可能拿到"prompt 个位数百分比"的项。 |
| **k8v4 与 int8 的差别** | 只在 **V 侧**：k8v4 的 V 是旋转 Q4_0（`kv_q4.cu` 已带 FWHT），int8 的 V 是 int8。**K 侧两者都是 int8，dp4a 通吃**。V 侧不能用 dp4a（概率是连续量），只能做 fp16 打包累加。 |
| **先做什么** | **A 组四条 exact（一车）→ B2（prefill 分数 dp4a，单独一车）→ B1（decode 分数，同一段数学搬过去）→ B3/C1 → wave64**。理由见 §4.0：B2 分母大（attn 16% of prompt）且 prompt 的可判性优于 decode。 |
| **只做一件的话** | **B2 + §4.1 的 Option 1 归约**：prefill 分数相位换 dp4a，但**保留现有 32-lane 归约拓扑**（每个 lane 的 8 维已同属一个 scale 组，先在 lane 内 int32 求和、转 float、乘本组 scale，再走原 reduce12）。改动面 = 一个 `dequant8+dot8` 函数 + q 的分组量化，**不碰归约、不碰 swizzle、不碰 softmax**。 |
| **行号能不能直接用** | **能**。生产与分支同为 0.1.57，`文件:行` 即产线行号；仅需回写两条陈旧记录（§7）。 |

---

## 1 判据（先钉死，避免"改了但说不清"）

| 门 | 用于 | 判据 |
|---|---|---|
| **G1 bitwise** | A 组（纯布局/归约序） | 同提示 LOGPOS 三份 md5 相同 + 答案 token 全同 |
| **G2 KL 门** | B 组（换指令/换累加精度） | 我们已有 `kl_prop` 管线，地板精确 0（P213）；KL ≤ 0.001 且 argmax 100% 才收 |
| **G3 2×CV** | 所有性能项 | **当次 run 的** 2×CV（P809），预热/停机按 P200 |
| **G4 三臂** | 有数值风险的项 | 候选 / 同 exe 自一致地板 / 对照（`strata-quant-quality-gate` 技能） |
| **G5 回滚件** | 每次装机 | D1/D2 由 `tools/deploy_gate.py` 强制，缺证据即 REFUSE |

---

## 2 项目找全性核查（本轮补的漏）

上版清单（`GFX906_OPT_INVENTORY.md`）只有三源：KI / 上游 llama.cpp / llama.cpp fork。**漏了两类**：

### 2.1 漏得最狠：Strata 自己的 gfx906 生态（9 个）

| 仓库 | 体量 | 里面是什么 | 对本方案的价值 |
|---|---|---|---|
| `NightPoetry/strata-gfx906-overlay` | 536 KB / 61 文件 | **port overlay**：`diffs/`（CMake 三处 `AND NOT STRATA_HIP_GFX906`）、`overlay/include/strata/hip_compat/*`（`cuMem*`→`hipMem*` VMM shim、cublas 映射）、`docs/PORT-NOTES-gfx906.md` | 16G MI50 上把 rich server 跑起来的完整配方；**我们的树已越过这一步**，但 `diffs/CMakeLists-gfx906.diff` 可对照检查有无遗漏的排除项 |
| `3chet/strata-gfx906-fieldnotes` | 287 KB / 49 文件 | 2×Radeon Pro VII 的实测台账，`04-what-not-to-tune.md` **17 条负面**（lookup-chain/suffix-draft/mtp-q4/pool-workers/prefill chunk/batch/rocBLAS 表填充/kv-grow/calibrate/kv-resident/pool-spin…） | **避免重做**：其中 6 条与我们队列重合（含 `--kv-resident` 净亏、rocBLAS `default` 行是判决不是空白） |
| `QPhuGit/Strata-gfx906-Argon` | 82 MB / 5682 文件 | 全树 + `include/strata/kernels/gfx906_dlops.hpp`（sdot4/udot4/dot2 封装）+ `bench/results/2026-10-08-gfx906-qsa-query-swizzle/` | **swizzle 的正式实测**：component **+14.65%**、整模型 prompt **+1.19%**、token 全同（正是我们的 `STRATA_GFX906_ATTN_QUERY_SWIZZLE`） |
| `freapsy/strata-mi50` | 75 MB / 5227 文件 | 同源全树（`mi50-gfx906` 分支），自述 115 tok/s decode | 配置基线对照 |
| `milpster/strata-dflash2-gfx906-mixed-rocm-cuda` | 272 MB | 全树 + `docs/work/rocblas-gfx906-workaround.patch` + **rocBLAS gfx906 段错误报告** | **风险输入**：缺 tuned 且缺 fallback 的 GEMM 形状会 SIGSEGV ⇒ 我们的 rocBLAS 表必须覆盖 fallback |
| `xxDoman/strata-gfx906` | 366 KB / 28 文件 | 0.1.43–0.1.48 **逐引擎版本**笔记（`docs/engines/*.md`）+ `docs/community-benchmark.md` | 版本间回归的旁证 |
| `MarcoTool/PDHyperMix-Strata-gfx906` | 150 KB | prefill/decode 分离部署 | 架构参考（非 kernel） |
| `Auirsword/z100l-strata` | 77 KB | 海光 Z100L（gfx906）单卡部署 + DTK 补丁 | DTK 路线，暂不适用 |
| `mixa3607/ML-gfx906` | 22 MB | 376★ 构建仓（含 Strata/llama.cpp/ComfyUI 镜像） | 构建入口 |

### 2.2 llama.cpp 侧漏的（12 个）

`incode0-debug/llama-cpp-gfx906-multibackend`（CUDA+HIP+Vulkan 单二进制）、`Kausik-A/gemma4-mi50-optimizations`（**Q8_1 复用 + fused QKV**，与我们的 N3 同题）、`Luskendeilder`/`mt4wss` 的 **SOLVE_TRI 崩溃修复**、`taobaoww2010-alt`（两个：编译补丁 / 优化版）、`dc740/gfx906`（memory-bound FA kernel）、`0FL01/gfx906-qwen3.8fn`、`DByte308/ornith-mtp-gfx906`、`phantomic12/ML-gfx906`、`bowmanjd/franken-llama`（nix）、`marki-nishicono/prism-llama-prod`（**0 字节空仓**）、`logicalor/llama.cpp_rocm_mi50`。

### 2.3 仍未覆盖的（明确说清，不算"找全"）

- **非 GitHub**：`skyne98.github.io/wiki-gfx906`（LDS/DPP/ISA 的原始实测，KI 与我们都在引用）、Docker Hub `unverbraucht/vllm-gfx906`、HF 模型卡讨论区。
- **私有/已删**：`marki-nishicono/*` 两个 0 字节仓、`taobaoww2010-alt` 的二进制。
- **结论**：**GitHub 公开侧已基本穷举**（关键词 `gfx906` / `MI50` / `Vega20` / `strata gfx906` 四组，按 star 与更新时间扫过）；**非 GitHub 侧只覆盖了 skyne98 一个来源**。

---

## 3 现状锚点（0.1.57 树，逐条 grep 过）

### 3.1 已经有的（不要再造）

| 能力 | 位置 | 说明 |
|---|---|---|
| gfx906 默认表 | `src/core/arch_defaults.cpp:63-82` | 两项 **bitwise** 默认开：`STRATA_GDN_HEAD=1`、`STRATA_GFX906_ATTN_REDUCE12=1`（12 head 用 16 次交换代替 60 次） |
| gfx906 tuned 包 | `:208-237`（`STRATA_GFX906_TUNED=1`） | 7 项：`ATTN_QUERY_SWIZZLE` / `GDN_PP=2` / `HC_Q8` / `SELECT_SIMT` / `ROUTE_TAIL_SKIP=7` / `MMQ_KQ=1`（KL .0171、+68% prompt）/ `HIP_PROMPT_F16=1`（KL .0026、~1.6× prompt） |
| decode GEMV 的 dp4a | `native_mmvq.cu:206-209,315-316,389,494-495,554-557` | `STRATA_DP4A` 已密布，**这一侧不用动** |
| prefill MMQ 的 dp4a | `iq_kernels.cu:84,103-192`（`#define ggml_cuda_dp4a(a,b,c) STRATA_DP4A(...)`） | 已在 |
| int8 KV 写/读 | `kv_q8.cu:33`（append）、`:78`/`:121`（gather 4/8-wide） | 量化按 **KV_Q8_GROUP=64** 一组一 scale |
| q4 KV + FWHT 旋转 | `kv_q4.cu:25`（`fwht256_kernel`）、`:100/121/141` | **k8v4 的 V 侧旋转已实现**（与 THEman 的 "FWHT rotation" 独立同源） |
| prompt attention 的 int8 K | `qsa_prompt_attn.cu`（KV_MODE 1/3/4）、`qsa_pattn.cu:86-110`（stage 16B 载入 + scale） | 已在，但**点积是 fp32**（见 3.2） |
| query swizzle | `qsa_decode_attn.cu:460-478`（`__builtin_amdgcn_mov_dpp`） | 已有；第三方实测 +14.65%（Argon） |
| 硬门 | `fused_gr.cu:3642` `if (prop.warpSize != 32)` 关掉 HC persist | 仍是 wave64 的唯一硬门 |

### 3.2 三个 dp4a 真空（本方案的主战场）

| # | 位置 | 现状 | 为什么是真空 |
|---|---|---|---|
| **V1** | `fused_gr.cu:114-121` `dot8q()` | 8 个 int8 用 `(float)(int8_t)(a>>8i)` + `fmaf` 逐个累加 | HC 占 decode 窗 **16.6%**（W835 §5），权重本来就是 Q8（`HC_Q8=1`），激活是 fp32 → 只要把激活变成 q8_1 就能一条 `v_dot4` 顶 4 条 FMA；且同文件 `gr_q8_tail()`（`:253`）**已经在产出 q8_1 镜像**，基础设施现成 |
| **V2** | `qsa_pattn.cu:141-172`（`dequant8` + `dot8`，被 `score_chunk_x` 调用，二次出现在 `:1581+`） | 每个 cell 每 head：8 次 `(float)c*sc` + 8 次乘加；12 head × 32 段 = **每 cell 3072 FMA + 256 反量化** | prompt attention 占 prompt 时间 **16%**（P104），这是 gfx906 上**唯一没有用上 dp4a 的大相位** |
| **V3** | `qsa_decode_attn.cu:54-63` `load8_q8` + `:180-215` 分数循环 | 同上结构；softmax 用 `warp_sum/warp_max`（`:31-38`，5 次 `__shfl_xor`） | decode attention 1.78 ms/窗；且 REDUCE12 只优化了**归约**，没优化**点积** |

---

## 4 移植清单

> 每条：来源 → 落点 → 改法 → 数值影响 → 门 → 预期 → 停机。

### 4.0 一页排序（改动量 / 可判性 / 上限收益）

| 项 | 改动量 | 可判性 | 上限收益 | 建议序 |
|---|---|---|---|---|
| A1 router DPP | ~30 行，5 处 | **G1 bitwise** | decode 8.5% 相位里的一部分，≤0.5 ms/窗 | 1 |
| A2 LDS +1 pad | ~10 行声明+索引 | **G1 bitwise** | 取决于 bank 冲突命中 | 1 |
| A3 softmax DPP | ~10 行 | **G1 bitwise** | 小 | 1 |
| A5 q8 gather 8-wide | 1 个编译宏 | **G1 bitwise**（注释自述） | gather 每层 2× 指令效率 | 1 |
| **B2 prefill 分数 dp4a** | ~60 行（1 个函数 + q 量化） | G2 KL | **prompt −2~4%（上限 6%）** | **2（单做首选）** |
| B1 decode 分数 dp4a | ~40 行 | G2 KL | decode −0.7~1.1% | 3 |
| B3 HC dp4a | ~40 行（有 q8_1 镜像现成） | G2 KL | decode −1~3% | 4 |
| C1 V half2 | ~30 行 | G2 KL（fp16 累加） | 取决于 V 相位占比 | 4 |
| A4 逐文件 max-ilp | 构建脚本 | G3 只有性能 | 中性~+2% | 与任一车同发 |
| **F1 载入暂存** | 1 个宏 + 8 轮循环 | **ISA 计数 + G3** | 已判否：−0.44% waitcnt | 不做（`P428`） |
| F3 half-warp 派发 / F4 预量化直喂 | 0.5–5 人日 | 见 F 组 | 见 F 组 | 判不适用 / 前置已否 |

**注意**：B2 与 B1 共用同一段数学，**先做 B2**——它分母大（attn 16%）、可判性更好（prompt 的 CV 比 decode 小），
而且做通之后 B1 只是把同一份 `dot8→dp4a` 搬到另一个文件。

### A 组：精确类（G1 bitwise，一次 A/B 可判）

| # | 项 | 来源 | 落点 | 改法 | 预期 |
|---|---|---|---|---|---|
| **A1** | **router 的三处归约换 DPP** | iacop `gfx906-common.cuh`（`v_add_f32_dpp`/`v_max_f32_dpp` 的 xor1/2/8 + xor4 双 `row_shl/shr` 拼法）；上游 #26466（未合，+121/−58）；W835 §3-2 | `native_router.cu:36`（和）、`:41`（max）、`:82-83`/`:136-137`/`:193-194`（argmax 双值） | 换 `__builtin_amdgcn_mov_dpp`；**xor16 保留 `ds_swizzle`**（iacop 同款） | router 3.84 ms/窗（8.5%）；DPP 单次交换 ~2× 于 LDS 路径（skyne98 1778 vs 906 Gxchg/s）⇒ 该 3 处合计 −0.3~0.6 ms 上限 |
| **A2** | **qsa_decode_attn 的 LDS 列式 +1 pad** | skyne98 实测 1865→3974 GB/s（2.13×）；KI `fattn-q8.cuh:942` `K_row_padding=16` | `qsa_decode_attn.cu:138-139`（`sq[G][HD]`、`sp[G][CHUNK]`）、`:354-355`（`spt[CHUNK][G]`，cell-major 正是列式消费） | 只改声明与索引，**不动算法** | 取决于 bank 冲突实际命中；先微基准（见 §6 Phase 0） |
| **A3** | **softmax 的 warp_sum/max 换 DPP** | 同 A1 | `qsa_decode_attn.cu:31-38`、`qsa_pattn.cu:65-74` | 5 次 `shfl_xor` → xor1/2/8 DPP + 末级 shfl | 每 cell 2 次归约；量小但零风险 |
| **A4** | **逐文件 `-mllvm -amdgpu-sched-strategy=max-ilp`** | KI `CMakeLists.txt:1626-1665`（gptq −15~26%、FA +2~5%、dense +7.7%；**MoE kernel −2.2% ⇒ 必须逐文件**） | **不在仓库 CMake**：生产 build.ninja 由 166 生成，落点是构建脚本里的 per-source flag | 只给 `qsa_decode_attn` / `qsa_pattn` / `fused_gr` 三个源文件加；其余不动 | 中性到 +2%，需 G3 |
| **A5** | **Q8_1 gather 的 8-wide 路径放出来** | 我们自己的 `kv_q8.cu:121`（8-wide，注释自述 bitwise）——**整个内核被 `#if defined(STRATA_EXPERIMENTAL_SM60)` 包住**（`:110`），**生产跑的是 4-wide**（`:223`） | `kv_q8.cu:110`（编译宏）、`:158`（`pre75_q8_gather()`）、`:210-220`（派发） | 把 wide 内核移出实验宏（或加 gfx906 专用宏）；判据不用改：HIP 下 `cc=10*major+minor` 对 gfx906 是 90 ≥ 75，`pre75_q8_gather()` 自然走 wide | gather 是 decode 每层必经；8B load + 16B store vs 4B + 8B |

### B 组：换指令（G2 KL 门 + G3）

| # | 项 | 来源 | 落点 | 改法 | 数值 | 预期 |
|---|---|---|---|---|---|---|
| **B2** | **prefill 分数用 dp4a**（**先做这个**） | KI `fattn-q8.cuh`（`static_assert(nbatch_K%4,"for sdot4")` `:429/:504`）；我们 `iq_kernels.cu` 的现成写法 | `qsa_pattn.cu:141-172`（`dequant8`/`dot8`）、`:112` 的 px 派发、`:1581+` 第二处 | §4.1 **Option 1**：lane 内 2 条 dp4a → `(float)s*(sq_g*sk_g)` → 现有 25-exchange 树不动；q 在 chunk 载入时按 64 组量化一次 | 新误差：q 的 int8 量化（K 已是 int8，不新增） | **现实带 prompt 2~4%（上限 6%）**；这是本方案唯一"个位数百分比"的来源 |
| **B1** | **decode 分数用 dp4a** | 同 B2 | `qsa_decode_attn.cu:54-63` + `:195-215`；**mode 3（k8v4）与 mode 1（int8）同一个模板 ⇒ 一处改动全覆盖**（§4.1 表） | 与 B2 同构；q 每步量化一次（12 head × 4 组，3072 个数），在做 LDS 暂存那一步里做，不新增 kernel | 同 B2 | **现实带 decode 0.7~1.1%（上限 1.5%）**；另加 MTP drafter（纯 int8）的 draft step |
| **B3** | **HC down-GEMM 用 q8_1 激活 + dp4a** | iacop `fused/mmq-prequantized.cuh`（预量化直喂）+ exabit 0001（fused norm 直接吐 Q8_1） | `fused_gr.cu:114-121`（`dot8q`）、`:253`（`gr_q8_tail` 已有 q8_1 镜像） | 把 `xn` 从 fp32 换成 q8_1 视图，`dot8q` → `STRATA_DP4A`×2 | 新误差：激活量化（1/127 相对） | HC 16.6% ⇒ **全局 −1~3%**；先做 roofline（HC 是否 ALU-bound） |
| **B4** | GDN 的 fp16 dot2 | iacop/fuutott `v_dot2_f32_f16`；KI `dense_gemv_gfx906.cu:88` `__ockl_fdot2` | `fused_gdn.cu:115-118`（现在是 bf16 位拼接 + fp32 fmaf） | 需先把权重转 fp16 | **bf16→fp16 丢指数范围**（fp16 5 位 vs bf16 8 位） | 只在 B1–B3 之后；**可能被 KL 门否掉**（W835 §4 已预警） |

### B 组附：B1/B2 的归约怎么改（唯一有设计难点的部分）

**先钉死"哪条路在跑"**（`qsa_decode_attn.cu:1204-1236`）：

| KV 格式 | `kv_mode` | 派发 | 进哪个 kernel |
|---|---|---|---|
| **k8v4** | **3** | `:1225` `STRATA_ATTN_CHUNK(3)` | `attn_chunk_kernel<3, LANE_CELL=false, QUERY_SWIZZLE=false, REDUCE12=false>` |
| **int8** | **1** | `:1231` | `attn_chunk_kernel<1, …>` |
| q4_0 | 2 | `:1228` | `<2>` |
| fp16 | 0 | `:1234` | `<0>` |

⇒ **一处改动同时覆盖 k8v4 与 int8**（同一个模板，K 侧都是 int8；差别只在 `load8` 的 value=true 分支读 v_q4 还是 v_q）。
另外：`_step` 这条生产 decode 路把 `LANE_CELL / QUERY_SWIZZLE / REDUCE12` 三个模板参数**全部取默认 false**，
所以 swizzle/reduce12 只在 `qsa_decode_attn_batch`（prefill/verify/MTP）里生效——这与我们 `PARAM_REGISTER` P55/P56
自己记的"在 k8v4 下不可达"一致。

现状数学（`qsa_decode_attn.cu:195-215`、`qsa_pattn.cu:156-172`）：32 个 lane，每个 lane 拿 8 个维度，
`dequant8` 反量化成 float，`dot8` 与 q 的 8 个维度做 8 次 FMA，得到**每 lane 的 float 部分和**，
再走 32-lane 的 fp32 树（`_step` 是 `warp_sum`；`_batch` 是 `reduce12` 的 16 次交换；prefill 是 `score_chunk_x` 的 25 次 exchange）。

换 dp4a 后有个硬约束：**`v_dot4_i32_i8` 出 int32，而 256 维跨 4 个 scale 组（KV_Q8_GROUP=64）**——
lane 0..7 属组 0，8..15 组 1…… 即 **int32 只能在 8 个 lane 内求和**，跨组必须先乘各自 scale。
但关键观察是：**每个 lane 的 8 个维度恰好落在同一个 64 组内**（8 | 64），所以"lane 内 int32 → 乘本组 scale → 变 float"
这一步**不依赖归约拓扑**，与现有树完全兼容。

| 方案 | 做法 | 指令数/ lane / head | 风险 |
|---|---|---|---|
| **Option 1（推荐）** | lane 内 2 条 dp4a（8 维 = 2×4）得 int32 `s`；`(float)s * (sq_g*sk_g)`（一组一个 scale，lane 内已定）；**原封不动**走现有归约（`_step` 的 `warp_sum` / `_batch` 的 reduce12 / prefill 的 25-exchange） | **4**（2 dp4a + 1 cvt + 1 mul）vs 现在 **16**（8 反量化 + 8 FMA） | **最低**：拓扑、swizzle、softmax 一行不碰；数值变化可解释（q 量化 + int32 中间积） |
| Option 2（后做） | 8-lane int32 树（3 次 int shfl），乘 4 组 scale 后跨组相加 | 3~4（dp4a 2 + shfl 摊薄） | 新拓扑；与 reduce12 的 head 置换（`qsa_pattn.cu:119-128`）冲突，要重写两处；只比 Option 1 好一点 |

**q 的分组量化放哪里**：
- decode：q 每步只有 **12 head × 256 = 3072** 个数，每个 64 组求一次 max（warp 归约）⇒ 48 个 scale。
  直接在做 LDS 暂存的那一步（`qsa_decode_attn.cu:150-165`）里做，**不新增 kernel**。
- prefill：q 是 n_q 行 × 3072，仍是每 block 一次（`qsa_pattn.cu:135 load_q_perm` 旁边）；
  成本 O(n_q×3072) 对 O(n_q×cap×3072) 的 MAC 可忽略（cap≈2112）。
- 顺手把 `sq_g*sk_g` 预算成 48 个 float 放 shared（每步一次）。
- **swizzle 不会破坏这个前提**：`QUERY_SWIZZLE` 只把 lane 的 8 个 q 元素在 [8l, 8l+8) 内换两半（`qflip=lane&4`），
  dim 组不变 ⇒ 组 scale 仍然唯一。

**精度账**：K 本来已是 int8（不新增误差）；q 变"每组 64 维、按组最大值缩放到 ±127"，组内相对误差 ~1/254，
分数相对误差量级 1e-3 ⇒ 正是 G2 KL 门能分辨的量级（我们地板精确 0，P213）。

**一个常被漏掉的收益点**：`--kv k8v4` 下 **MTP drafter 跑纯 int8**（`src/core/mtp.cpp:390` `qsa_set_kv_int8(true)`），
所以 B1 同时改善 draft step。



### C 组：k8v4 / int8 专有

| # | 项 | 落点 | 改法 | 说明 |
|---|---|---|---|---|
| **C1** | **V 侧 fp16 打包累加** | `qsa_decode_attn.cu:230-260`（`acc[G]` 的 fmaf）、`qsa_pattn.cu:320-330`（`a[d][h]=fmaf(ww,v,…)`） | 两条链合 `__hfma2`（fp16 累加）或至少把 V 反量化成 half2 再乘 | 数值变（fp16 累加），**必须 G2**；理论上 ALU 减半 |
| **C2** | **int8 模式的 V 侧 dp4a（探索）** | 同上 | 把概率 p 量化成 int8（按 chunk 最大值缩放到 2^14，v70 kernel 就是这么干的），再 `dot4(p_int8, v_int8)` | 仅 `--kv int8`；k8v4 的 V 是 q4，填不进 int8 dot ⇒ **两种模式收益不同**，必须分开测 |
| **C3** | **k8v4 的 V 旋转** | `kv_q4.cu:25` + `layer.cpp:1282`（`fwht256_inplace_cuda(b.qcur)`） | **已实现，不动** | 只做一件事：确认 `--kv int8` 下 `kv_rot=false` 是否成立（`layer.cpp:822` 说 `kv_rot = kv_q4 \|\| (kv_int8 && g_kv_int8_rot)`） |

### D 组：结构性（大工作量，最后）

| # | 项 | 落点 | 说明 |
|---|---|---|---|
| **D1** | **wave64 布局** | `fused_gr.cu:3642` 硬拒；`native_router.cu:324` 的 `<<<n_tok,32>>>` 半个 wave；`warp_sum` 全按 32 lane 写 | HC persist 是 gfx1030 写法，改 64 lane 要重排寄存器布局（W835 估"以周计"） |
| **D2** | **grid/CTA 顺序与 CU 均衡** | 我们按专家/tile 铺 grid 的 kernel（`iq_kernels.cu` 的 grid.z 分专家、`native_router.cu`） | 上游 #31599 实测：同一 kernel 换 grid 顺序，gfx906 MoE prefill 差 **15~100%**（最忙 CU = 平均 4×）。**判据**：rocprofv3 的每 CU `SQ_INSTS` 方差 + 最忙/平均比 |
| **D3** | **rocBLAS 表的 fallback 覆盖** | 生产 `gfx906-rocblas-5.5.0.txt`（W830） | milpster 的报告：**缺 tuned 且缺 fallback** 的形状会让 rocBLAS 空指针崩（ROCm 6.1/6.4）。核对我们的表是否覆盖全部在跑形状 |

### E 组：明确不做（附证据）

| 项 | 理由 |
|---|---|
| MFMA / WMMA / tensor-core 路径 | gfx906 无此指令（`llvm-mc` 实测 + 上游 `AMD_MFMA` 只给 CDNA） |
| bf16 直算 | 无硬件 bf16；实测 4.40× 代价（KI RECON） |
| TurboQuant 2/3-bit KV | 我们 KV 是 816 B/cell 的 k8v4，瓶颈在专家与 HC，不在 KV 容量；且 2-bit 要过 KL 门 |
| LDS staging 共享激活 | exabit 十次构建：−16~−52%（barrier） |
| 整块 32 权重/线程 | batch>1 时 −16~−32%（只在 batch 1 +5%） |
| `--kv int8` 直接当默认 | 若 prefill 变慢 2.5~2.7×（KI 实测），只买容量；**待 C2 之后再判** |
| 用 `STRATA_GFX906_DEFAULTS=0` 关表 | 那是回滚开关，不是优化 |

---

### F 组：手法（**能拿的不是文件，是这四条**；每条都给了判据 / 样本 / 停机 / 成本）

> 2026-11-07 07:0x 补（机主：「你怎么拿手法。能拿你拿呀。入权威调优或者移植方案啊。」）。
> 本组与 A–D 组的区别：A–D 是「改哪个文件」，F 是「搬哪个写法」。宿主量化不同（iacop 吃 Q4_0/Q8_0、
> exabit 吃 Q8_0 激活），**文件不能直用**，但写法可以，且必须落到**我们的**量化（Q4_K 权重 / int8·k8v4 KV）。
> 每条都必须回答四样：判据用哪一列数、样本量、停机条件、成本。

| # | 手法 | 来源（宿主） | 我们落到哪 | 判据 / 样本 / 停机 / 成本 | 现状与判决 |
|---|---|---|---|---|---|
| **F1** | **载入暂存**：把每轮的权重 global load 先攒进寄存器，再统一写 LDS（把「1 载入→1 写」变成「N 载入→N 写」） | iacopPBK `matmul/mmq.cuh` 的 `GFX906_LOAD_TILES_Q8_0_ASYNC` / `_LDS_LEGACY`（**Q8_0**） | `mmq-load-tiles.cuh:711` 的 `ggml_cuda_mmq_load_tiles_q4_K`（dp4a 分支） | **判据 = ISA 的 `s_waitcnt` 与 `global_load`/`ds_write`/`v_dot4` 计数 + 2K/8K prefill 的 2×CV**；样本 = 每个 arm n≥3；停机 = 开窗时 1 次重启；成本 = 1 次全量重编（≈3 min，无 GPU） | **已拿、已判否（W1037，`P428`）**：编译通过（`-DSTRATA_GFX906_MMQ_STAGE`），ISA 实测 **`s_waitcnt` 6192 → 6165（−0.44%）**，`global_load` 3788 / `ds_write` 289 / `v_dot4` 5184 **逐项相同** ⇒ 编译器本来就把 8 次载入排到一起了（`STEP = nrows×nwarps = 4×4 = 16`，`I = 128` ⇒ **8 轮**），手工暂存只省 27 条等待。**期望 <1%，低于 2×CV，不开窗**；代码留在 `gfx906/port-all` 默认关 |
| **F2** | **DPP 归约**：`v_mov_b32_dpp` 的 xor1/2/4/8 代替 `ds_bpermute`/`__shfl_xor` | iacop `gfx906-common.cuh`；skyne98 实测 1778 vs 906 Gxchg/s | `native_router.cu` 三处归约 + top-k 交换（A1）；`qsa_decode_attn.cu` / `qsa_pattn.cu` 的 softmax（A3） | bitwise（同操作数对、同序）⇒ 只判速度；样本 n≥3；停机 1 次重启；成本 0（已在 pa1 里） | **已拿（A1/A3），待窗口**：`STRATA_GFX906_ROUTE_DPP` / `STRATA_GFX906_ATTN_DPP`，开关在 pa1 二进制里可见（`strings` 5/5） |
| **F3** | **half-warp 32 线程派发**：小矩阵（MoE、batch=1）用 32 lane 而不是 64 lane，减少半个 wave 的空转 | iacop `mmvq.cu`（`Q4_0/Q4_1/Q8_0` 的 warp 协作 MMVQ） | decode 的 MMVQ / MoE 小矩阵；**prefill 的 MMQ 是 tile 化的，用不上** | 判据 = decode ms/窗（**只设「不劣化」门**，2026-11-02 定：单流 decode 已在地板，收益不作成功判据）；样本 n≥5；停机 1 次重启；成本 ≈0.5 人日 | **不拿（判不适用）**：① gfx906 只有 wave64，32 lane 意味着半个 wave 空转，而 iacop 的收益来自「小矩阵下少一次归约」；② 我们的 decode 已经在 70.7 tok/s 的地板上（`§0.2` 第 1 条硬约束），这一条最多改 decode，按现行验收口径**没有收益可记** |
| **F4** | **预量化直喂**：norm/epilogue 直接吐 Q8_1，MMQ / MMVQ 不再自己量化激活 | exabit `fused norm 直吐 Q8_1`；iacop `fused/mmq-prequantized.cuh`（**Q8_0 激活侧**） | 与我们 `STRATA_QFUSE` 同题；要动的是 MoE 预填的激活量化链 | 判据 = prefill 2×CV + KL（改的是量化发生的位置，不是精度）；样本 n≥3；停机 1 次重启；成本 3–5 人日 | **不拿（前置已否）**：`B3` 的前提被 `P421` 否掉（decode 的整数点积不是 ALU-bound，A0 实测零结果）；且这条真正省钱的地方是「省掉一次 12 MB 级的激活搬运」，只在 `wait copy` 相位可见——我们的 `wait copy` 在 2.5K 只占 1.2%（`§0.1`）⇒ **分母不够** |

**F 组的一句话**：**这四条里只有 F2 值得测（已在 pa1），F1 已用 ISA 判否，F3 被验收口径判不适用，F4 被前置判否。
「能拿的都拿了」这句话现在有证据——证据不是我说拿得动，而是编译日志与指令计数。**

## 5 k8v4 与 int8 的成本模型（为什么 K 侧能砍、V 侧砍不动）

单 cell、单层、单 KV head（HD=256、G=12、NSC=4）：

| 阶段 | k8v4（K int8 + V q4） | int8（K/V 都 int8） |
|---|---|---|
| K 读 | 256 B + 4 scale | 256 B + 4 scale |
| K 反量化 | 256 次 `(float)c*sc` ≈ 512 ALU | 同左 |
| 分数 | 12 × 256 FMA = **3072** | 同左 |
| V 读 | 128 B（q4）+ 4 scale | 256 B + 4 scale |
| V 反量化 | q4 解包 256×~3 ≈ 768 + 256 乘 | 256 乘（512 ALU） |
| V 累加 | 12 × 256 fmaf = **3072** | 同左 |
| **合计 ALU/cell** | **≈ 7424** | **≈ 7168** |

**dp4a 能动的只有 K 的"反量化 + 分数"那 3584**（≈48%）：
- 改造后：q 量化 12×256 一次/步（按 cap=2112 摊薄 ≈1.5/cell）+ 每 cell 12×64 = **768 dp4a** + 48 次 scale 乘。
- **V 侧不动**：概率是连续量，`v_dot4` 需要两个 int8 向量。C2 的 p→int8 是唯一出路，但那是**新的量化误差来源**，且只在 int8 模式下有意义。

⇒ 两个直接推论：
1. **B1/B2 的收益与 KV 格式无关**（K 侧两种模式都是 int8）⇒ 可以先用生产的 k8v4 测，不需要切 int8。
2. **int8 模式相对 k8v4 多出来的成本在 V**（256 B vs 128 B、512 vs ~1024 ALU），所以"int8 省显存但更慢"是结构性的，不是调参能救的。

### 5.1 条目 × KV 格式覆盖矩阵（"同步考虑 k8v4 和 int8"的答案）

| 条目 | k8v4（mode 3） | int8（mode 1） | q4_0（mode 2） | fp16（mode 0） |
|---|---|---|---|---|
| A1 router DPP | ✅ 同 | ✅ 同 | ✅ 同 | ✅ 同 |
| A2/A3 LDS pad / softmax DPP | ✅ `attn_chunk_kernel<3>` | ✅ `<1>` | ✅ `<2>` | ✅ `<0>` |
| A5 q8 gather 8-wide | ✅ 只影响 K 侧 gather | ✅ | ❌（走 `kv_gather_q4_step`） | ❌ |
| **B1 decode 分数 dp4a** | ✅ 一处改动 | ✅ **同一模板** | ⚠️ 要先 q4→int8 解包（+2 op/8 维），收益小于 int8 模式，不在首选 | ❌（K 是 fp16） |
| **B2 prefill 分数 dp4a** | ✅ `launch<3>` | ✅ `launch<1>` | ⚠️ 同上（prompt 里 q4 是 mode 4，scale 每 32 一组） | ❌ |
| B3 HC dp4a | ✅ 与 KV 无关 | ✅ | ✅ | ✅ |
| C1 V half2 累加 | ✅ V 是 q4 反量化后 | ✅ V 是 int8 反量化后 | ✅ | ✅ |
| C2 V 侧 dp4a | ❌（V 是 q4） | ✅ **仅此模式** | ❌ | ❌ |

⇒ 结论：**A/B3/C1 与 KV 格式解耦；B1/B2 覆盖 k8v4 + int8 两种；C2 只对 int8 有意义。**
我们产线是 k8v4 ⇒ **按 k8v4 测就能拿到 A+B1+B2+B3+C1 的全部收益**，int8 只在切换格式时才需要单独复核。

---

## 6 分阶段执行（每阶段一车，先汇总再下一车）

### Phase 0 — 微基准（**不停服**，~40 min）

四个独立 kernel（写进 `albus/gfx906_survey/bench/`，**不碰生产**）：
1. DPP xor1/2/4/8 vs `shfl_xor` 的 32-lane 归约：`Gxchg/s`（复现 skyne98 的 1778 vs 906）。
2. LDS 列式读 `ld=32` vs `ld=33`：`ds_read_b128` 带宽（复现 1865→3974）。
3. **K 分数两种写法**（256 维、12 head）：`dequant8+dot8` vs `q8 量化 + dp4a`，量指令数与时间。
4. **q8_1 镜像复用**：HC 形状（D=2048? 按实际）下 `dot8q` vs `dp4a`。

**出闸判据**：3、4 两项若 dp4a 版本 <1.3× 于现状，则**B1/B2/B3 全部降级**（说明这些相位不是 ALU-bound，而是 load/延迟-bound）。这一步能省掉后面两周。

### Phase 1 — A 组（**停服 3 min**，一车）

`A1 + A2 + A3 + A5` 一起上（全 exact），`A4` 单独编一版二进制（编译期，不影响 A/B 逻辑）。
- 验收：G1（LOGPOS md5 相同）+ G3（ms/win、router 相位、read 三档）。
- 回滚：`STRATA_GFX906_DEFAULTS=0` 或还原二进制。

### Phase 2 — B2（**单独一车**，做通它）

prefill 分数 dp4a（§4.1 **Option 1**）。这是最大项，也最可能改变 prompt 数字，单独测、单独回滚。
- **上限算术**：attn 占 prompt 16%（P104）；分数相位约一半 ⇒ 8%；ALU 4× ⇒ 最多 **6%**；**现实带 2~4%**。
- 用 3 档 read（1958 / 3718 / 6666）+ 8×128 decode 同时看（防"prompt 快了 decode 慢了"）。
- 只改 `qsa_pattn.cu:141-172`（`dequant8`/`dot8`）与 q 的分组量化；**V 累加与 softmax 一行不碰**（那是 Phase 4）。
- 先跑 G4 三臂，KL 门过再进生产。**若 <2×CV，直接否**（P809：判据用当次 run 的 CV）。

### Phase 3 — B1（**同一段数学搬到 decode**）

decode 分数 dp4a。`qsa_decode_attn.cu:54-63` + `:195-215`；**k8v4（mode 3）与 int8（mode 1）同一个模板，一处改动全覆盖**（§4.1 的表）。
- **上限算术**：decode 窗 44.98 ms（W828 §6.12），attention 1.78 ms = **3.96%**；分数相位约占一半 ⇒ 0.89 ms；
  ALU 4× ⇒ 最多省 0.67 ms = **1.5%**；**现实带 0.7~1.1%**。
- 因为是"搬运"，风险主要在 q 量化的位置（decode 每步都要做）——Phase 2 已把这段代码写好，这里只换调用点。

### Phase 4 — B3 / C1

B3（HC dp4a）与 C1（V half2）**分开**，因为一个动 K 侧一个动 V 侧，混在一起就归因不了。

### Phase 5 — D1 / D2

D2（grid 顺序）先做——不动代码，只改 launch 配置，成本最低；D1（wave64）按周排。

---

## 7 风险与回滚

| 风险 | 处置 |
|---|---|
| **记录与产线不一致** | 产线已是 0.1.57（机主确认），但 `deploy/SESSION_STATE.md:11`（`strata-0.1.55t`）与 `PARAM_REGISTER` P262/P263（`/src=0.1.56`）仍写旧值 ⇒ 本轮结束时**只回写记录，不动代码**；否则下一轮会按错版本去定位行号 |
| 改源码 = 改生产资产 | 一律走 `build.ninja` 的 flags 逐字抄；改完先 `deploy/tools/deploy_gate.py`（D1–D6），缺证据 REFUSE |
| KL 门可能否掉 B1/B2 | 预设退路：只对 decode 开（B1），prefill 保持 fp32（B2 若 KL 超 0.001 就否） |
| rocBLAS 形状崩溃（milpster 报告） | D3 先核对表覆盖；一旦出现 SIGSEGV 先怀疑 rocBLAS 而非我们的 kernel |
| 半波浪费 | `native_router` 的 `<<<n_tok,32>>>` 在 wave64 上只跑半个 wave；A1 之后顺手评估（是否改 64 线程） |
| **不能照搬"别的架构的开关"** | W835 §11 已实测：gfx12 表里 4 项 bitwise 收益，在 gfx906 上是 0（decode）/ −4.5%（prefill）。本方案每条都要求在 gfx906 上**单独测**，禁叠加测 |

---

## 8 一句话回答"项目是否已找全"

**没有——上一版漏了整个 Strata gfx906 生态。** 本轮补齐 12 个仓库（9 个 Strata 系 + 3 个 llama.cpp 系真代码），
并把"仍未覆盖"（skyne98 wiki 之外的博客、Docker Hub、HF 讨论、私有仓）明确列出，不再假装穷举。
其中**三条直接影响方案**：Argon 的 swizzle 实测（+14.65% component / +1.19% 整模型）、3chet 的 17 条负面（省掉重做）、
milpster 的 rocBLAS 崩溃报告（D3 必查）。

---

## 9 证据索引

| 内容 | 路径 |
|---|---|
| 本方案锚点（0.1.57 全树） | `albus/gfx906_survey/src/Strata-gfx906-mi50/` |
| 三源清单（上一版） | `albus/gfx906_survey/GFX906_OPT_INVENTORY.md` |
| Strata overlay / 笔记 | `fork_misc/np_*`、`fork_misc/chet_*`、`fork_misc/argon_*`、`fork_misc/milp_*` |
| fork 源码 | `fork_iacop/*`、`fork_misc/*`（exabit 补丁清单 / THEman / JeanP00l） |
| 上游 PR 补丁 | `pr/*.txt` |
| 复现脚本 | `_gh.py` `_raw.py` `_prfiles.py` `_cdetail.py` |

---

## W1042 移植状态（2026-11-07，机主 15:26「移植 gfx906 专用的 dot8 和 dot4 两个核心」）

| 核心 | 指令 | 生产树位置 | 状态 |
|---|---|---|---|
| **dot4** | `v_dot4_i32_i8` | `include/strata/platform/hip_compat/strata_hip.h:236-247`（`strata_dp4a` / `__dp4a`） | **早已在产且是硬件指令**：拆 fatbin 后 `qsa_decode_attn.cu.o` 有 **384 条**、`v_mad_i32_i24` 0 条。W1036/A0 改的 `include/strata/hip_compat/intrinsics.hpp` **不在任何 depfile 里**，是死文件；本轮给它加警示并把 A0 分支同步过去，防止下一个人再改错文件。 |
| **dot8** | `v_dot8_i32_i4` | 新增 `strata_hip.h::strata_dp8a/__dp8a` + `include/strata/kernels/gfx906_dot.hpp` + `tools/gfx906_dot48_selfcheck.cu` | **核心已移植、自检通过、尚无生产调用点**（`R108`）。8192 随机 + 9 边界用例 dot4/dot8 均 0 mismatch，`HW_device=1`，自检设备 ISA `v_dot4=1 / v_dot8=1`；候选二进制与 `attn` 逐字节相同，因为新 helper 被 DCE。 |

**硬件前提（`llvm-mc -mcpu=gfx906` 与 ROCm `AMDGPUAsmGFX906` 核实）**：`v_dot4_i32_i8` / `v_dot8_i32_i4` / `v_dot2_f32_f16` 在**具体 gfx906 目标**上可用；`v_dot4c` / `v_dot8c` **不可用**；`gfx9-generic` 目标会排除这些指令 ⇒ 构建必须 `--offload-arch=gfx906`（`build-masterp/build.ninja` 的 FLAGS 实测如此）。`sdot4/sdot8` 的第 4 参数 `clamp=false` 时 int32 累加器**回绕**（自检溢出用例已验），与 CUDA `__dp4a` 的模 2^32 契约一致。

**接入面（未做，别当成完成）**：k8v4 的 V 是 4-bit code，正好能填 dot8 的一个操作数，但 softmax 概率是 float ⇒ 需要 `p→int4` 量化（新误差源，见 §C2）+ 自带锚臂的数值门 + max-context needle。先做 roofline 判 attn 是否 ALU-bound：`GFX906_OPT_INVENTORY §8` 已记「ALU 换指令在 gather 型 kernel 上无效，dp4a 已满速」。

---

## W1046 执行更正与新增候选（2026-11-07；并入 W832 §0.1 的 R109/R110）

1. **B2 不再是独立待移植项**：`qsa_pattn.cu` 在 HIP 下不编译，gfx906 prompt 实际回退 `qsa_decode_attn_batch`；W1044 的 DP4A 已覆盖该数学。此前「B2 > B3、B2 还可再拿 2–4%」排序作废。
2. **B3 已进入实现**：`gfx906/hc-dp4a @ 179bd6b5` / `hc4`，默认 off；Q8_0 down 权重与 staging 量化的 int8 激活做 DP4A，原内核保留。ISA `v_dot4=720`，parity/bench 功能门过；激活量化导致 mixed rel-RMS 约 0.0009→0.0012，必须再过节拍内数值/任务/A-B 门，未装机。
3. **A1/A5 不再笼统排队**：A1 在 B3 后独立 bitwise + decode A/B；A5 受 `P425` 的死派发约束，未证明生产调用点前不投入。A2/A3 每个位单独测，A4 最后逐 TU。
4. **k8v4 dot8 = R110**：不是 `dot8q()`；首选 PV 的 `P(int4)×V(int4)` 8-cell 原型，QK 的 Q→int4 暂缓。原型先过误差与微基准，未过不接 OPT、不占生产窗口。


**W1046/P525 原型**：ROCm/LLVM 规格为 i4x8×i4x8；CPU/GPU 对齐，预打包 1.483×，合成 rel-rms 6.23%。仅证明可行性与上限，未过模型质量门。
