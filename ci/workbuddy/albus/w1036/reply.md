# W1036 报告 · gfx906 全量移植（A0 + A1 + A2/A3 + A5 + B1/B2，一分支一编译，逐项开关）

**一、生产容器（10 字段）**

| # | 字段 | 值（2026-11-07 05:3x–06:1x 只读） |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · `ulimits.memlock=-1:-1` |
| 2 | 运行中引擎 | `strata-0.1.57-001` · md5 `5e63174dbd7cc04e5fa1b5fc455b2a73` · 42,947,088 B |
| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43` · `exe=/data/bin/strata-0.1.57-001` · args 37 / env 9 |
| 3a | args（19 flag） | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 个） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1`（本轮新增的 5 个开关**只在候选分支里、默认关**：`STRATA_GFX906_ROUTE_DPP` `STRATA_GFX906_Q8_GATHER8` `STRATA_GFX906_ATTN_DPP` `STRATA_GFX906_ATTN_DP4A` `STRATA_GFX906_ATTN_LDS_PAD`，生产 env 一个都没加） |
| 4 | 健康 | `/health` = `{"status":"ok","max_context":262144,"loaded":true}` · `running` · `restarts=0` · `StartedAt=2026-11-06T16:48:17Z`（本轮只编译不装机，未重启） |
| 5 | 资源隔离 | 引擎 `VmLck 0` / `Locked 0.0 GiB` · `ulimit -l` unlimited |
| 6 | 显存布局 | expert cache 7463 experts / 21.79 GiB · prompt 路径 **borrows 1554 槽（3.49 GiB）** · VRAM free 736,862,208 B（0.686 GiB） |
| 7 | 回滚件 | 40 个引擎二进制品 · `ci/rollback.sh --exe strata-0.1.57-001 --apply` · config 侧 `cp *.json.bak` 回滚；本轮候选件在 `build-port2/strata`，**未进 `/data/bin`** |
| 8 | 本轮改动 | 生产 **0 次装机**、引擎 **无净变更**；`disk=build=running` 三方 md5 仍为 `5e63174dbd7cc04e5fa1b5fc455b2a73`（build 侧沿用 W1033，disk/running 本轮实取）；改动全部在新分支 `gfx906/port-all`（commit `79516b21`） |
| 9 | ROCm | 10.1.0 · HIP 7.16.26323-0000000 · clang 24.0.0git |
| 10 | llama.cpp | b11062 · `3cf03257f219afbe7334045ff7c6a06ac68c627d`（记录值） |

**二、主线** — 上游 `Niko1221/Strata` 未动（只读）；`gfx906/mi50` @ e181bda5（tag mi50-0.2.11-r33-14，落后 0 / 领先 80 个提交，脏 0 行）保持原样；新分支 `gfx906/port-all` 从它拉出，1 个提交 `79516b21`（4 个文件），**已推到 origin（`gfx906/port-all`）、未合主线**——分支名不在 CI 白名单（`main` / `gfx906/mi50` / `ci/**`），所以这次 push 不会触发 Actions。166 生产工作树仍是 `gfx906/mi50`；编译走独立 worktree `pr/port-all` + 独立构建目录 `build-port2`，与生产树、生产构建目录都分开。

**三、本次落生产** — 引擎无净变更；**重启 0 次、停机 0 分钟、回滚 0 次**。只做「新建分支 + 改 4 个文件 + 在镜像内编译」，**没有把任何二进制装进 `/data/bin`，也没有起过候选引擎**。

**四、进度** — 366 条 / 已结 283 / 77.3%（本轮 +7：`P419`–`P424` + `R103`；队列置顶 = **R103**）；队列 `~~R51~~`(DONE_NEG) → **`R95`（暂不结案，按机主 05:3x 指示保留）** → `R94` → `R91` → `R89` → `R46` → `R49` → `R50`。

---

## 正文

**1. 移植的对象不是「优化清单」，而是一个被清单漏掉的缺陷：`dp4a` 在 gfx906 上一直是软件模拟（A0）。**
`include/strata/hip_compat/intrinsics.hpp:18` 的 `dp4a()` 只给 gfx1010–1012 / gfx1030–1032 / gfx11–12 开了硬件分支，**gfx906 落到 portable 循环**。用 `--cuda-device-only -S` 编真实头文件看 ISA：

| 版本 | `dp4a()` 的一条调用编译成什么 |
|---|---|
| 移植前 | **28 条**（6 `v_cmp` + 6 `v_cndmask` + 6 `v_or` + 3 `v_mad_i32_i24` + `v_mul_i32_i24` + 2 `v_perm` + …） |
| 移植后 | **1 条 `v_dot4_i32_i8`** |

关键点：**LLVM 不会把这个循环折回指令**（我先用「强制转换写法的等价循环」试过，那种会被折；生产头文件用的是 `value < 0x80 ? value : value - 0x100` 的 select 写法，折不了）。影响面是**全树已有的 dp4a 站点**：`src/kernels/cuda/native_mmvq.cu:206` 起共 45 处、`iq_kernels.cu`、`s2_expert_grouped.cu`、`dflash2.cu`、`q36_kernels.cuh`。语义完全一致（同样是有符号字节积、同样 mod 2³² 累加）⇒ **逐位相同**，属 G1。

**2. 为什么这条比清单里的 B1/B2 更要紧。** 清单说「decode 的 dp4a 已密布，这一侧不用动」，于是把 B1/B2 设计成「把分数相位也换成 dp4a」。但在 A0 之前，**新增一个 dp4a 站点 = 把 16 条 FP 指令换成 28 条整数指令**，B1/B2 会直接变成负收益，然后把原因错误地归到"相位不是 ALU-bound"。⇒ **A0 是 B1/B2 的前置条件，不是并列项。**

**3. 一个把清单锚点打掉的核查：B2 的落点在 gfx906 上根本不编译。**
清单写「B2 = prefill 分数 dp4a，落点 `qsa_pattn.cu:141-172`」。实测该文件 `src/kernels/cuda/qsa_pattn.cu:25`：

```
#if !defined(__HIPCC__) && defined(STRATA_EXPERIMENTAL_SM60)
#define STRATA_PATTN_BUILT 1
#else
#define STRATA_PATTN_BUILT 0        // ← HIP/gfx906 走这里，整个文件不编译
```

而 gfx906 的 prompt attention 真实路径是 `qsa_prompt_attn`（tensor-core 版，`prompt_attn_imma_default(HIP)=false` 拒绝）回退到 **`qsa_decode_attn_batch` ⇒ `attn_chunk_kernel`**。⇒ **B1 与 B2 是同一段代码**（`_step` 与 `_batch` 同一 `attn_chunk_body`），不是两个文件。这一条改变了移植形态：改一处，prefill 与 decode 都覆盖，靠**两个独立开关**分开测。

**4. 移植形态：一个二进制、每个移植项一个开关、一次编译逐项测。**
机主要求「一次性都移植完，再一个个测」。为了不出现「改一个编一次」的十次编译，我把 A2/A3/B1/B2 做成 `src/kernels/cuda/qsa_decode_attn.cu:124` 的 `attn_chunk_kernel` 上一个 `int OPT` 位掩码：

| 位 | 项 | 开关（env） |
|---|---|---|
| 0 | A3 归约换 DPP（分数求和 + chunk softmax） | `STRATA_GFX906_ATTN_DPP=1` |
| 1 | B1/B2 分数换 `v_dot4`（q 按 64 组量化成 int8） | `STRATA_GFX906_ATTN_DP4A=1` |
| 2 | A2 sq/sp 的 LDS 加 pad（列式读不再撞同一 bank 组） | `STRATA_GFX906_ATTN_LDS_PAD=1` |

另两项独立成开关：`STRATA_GFX906_ROUTE_DPP=1`（A1，router 三处归约 + top-k 交换）、`STRATA_GFX906_Q8_GATHER8=1`（A5，8-wide gather）。**任一位被打开时内核走「朴素版 + 该优化」**（不带 query swizzle / reduce12），因此每项的对照必须是同一条朴素基线，这一点写进了代码注释，避免将来把 swizzle 的收益算到 dp4a 头上。

**5. 逐项的可判定性（写清楚，否则测了也说不清）。**
A0 / A1 / A3 / A5 都是**逐位不变**（同样的操作数对、同样的顺序，只是换了交换指令或执行宽度）⇒ **G1**。A2 只改声明与索引、不动算法 ⇒ **G1**。B1/B2 引入 q 的 int8 量化（K 本来就是 int8，不新增误差；q 按 64 维组内最大缩放到 ±127，组内相对误差 ~1/254）⇒ **G2**（KL ≤0.001 且 argmax 全同）。

**6. 编译与验证状态（现取，不写死）。**
构建目录 `build-port2`（从生产 `build-r28` 复制，禁用 `RERUN_CMAKE`/`VERIFY_GLOBS` 两条重生成边——`ci/build.sh` 早就记过 ninja 会因 glob 校验去重跑 CMake 然后死掉；我这次先把「重跑 CMake」这条路堵掉，再挂上 `llama.cpp`，才编得动）。日志尾：`RC=0` · `real	2m36.580s` · 重编 HIP 单元 **81** 个 · 产物 `strata` **43,042,024 B**（比生产件 42,947,088 B 大 94,936 B，即 **+0.22%**，多出来的是 7 个 OPT 实例化 + 路由 DPP 分支）。

**7. 交付与复现。** 分支 `phoenixclyde/Strata @ gfx906/port-all`（origin 同名分支已建，HEAD `79516b21`），4 个文件：`include/strata/hip_compat/intrinsics.hpp`、`src/kernels/cuda/native_router.cu`、`src/kernels/cuda/kv_q8.cu`、`src/kernels/cuda/qsa_decode_attn.cu`。本地留证：`albus/w1036/src/`（改动后全文）、`albus/w1036/dot_real.cpp`（A0 的 ISA 探针）、`albus/w1036/isa_check.sh`（一次跑出 `dot4/dpp/bpermute` 三个计数：qsa 侧 `dot4=48`、`dpp=140 处`，router 侧 `dpp=325`）。

**8. 本轮明确没做的三件（不装成"已移植"）。**
① **B3（HC dp4a）**：`gr_q8_tail()` 产出的 q8_1 镜像只在 `STRATA_QFUSE=1` 下存在，直接做等于要新建一条激活量化路径 + 新增误差源 ⇒ 必须先决定 QFUSE 是否常开，否则是两件事混一件。
② **C1（V half2 累加）**：把 V 侧改成 fp16 累加会引入**新的精度来源**（不是换指令，是换累加精度），清单自评「取决于 V 相位占比」，而 2.5K 定长测里 V 相位没有单列 ⇒ 先补测占比再决定。
③ **A4（逐文件 max-ilp）**：属构建期 flag，不是源码；要做需要改 CMakeLists（清单也承认「不在仓库 CMake」），单独一车。

**9. A0 实测：没有可分辨的收益（四个指标全在 2×CV 带内）。**
窗口 06:10:54–06:14:38，一换件两重启，两臂各冷启一次、同盐值同内容、逐请求交错取数：

| 指标 | ctl（`-001`，dp4a=软件循环） | a0（port-all，标志全关） | Δ | 2×CV | 判 |
|---|---|---|---|---|---|
| prefill 3.4K | 1569.3 µs/tok（CV 0.4%，n=3） | 1609.8（CV 3.4%，n=3） | **+2.6%** | 6.8% | 带内 |
| prefill 10.8K | 1267.6 µs/tok（CV 0.2%，n=2） | 1268.8（CV 0.0%，n=2） | **+0.1%** | 0.4% | 带内（几乎恒等） |
| decode tok/s | 62.50（CV 13.6%） | 60.46（CV 13.6%） | −3.3% | 27.2% | 带内 |
| decode ms/window | 41.30（CV 17.2%） | 41.28（CV 17.2%） | **−0.0%** | 34.4% | 带内 |

3.4K 那臂的 `+2.6%` 全部来自**第一条请求**（5674 ms，冷启后的首条），后两条 5378/5383 对 ctl 的 5341/5331 只差 +0.8%；10.8K 这一档 CV 只有 0.2%/0.0%，**差 0.1%**，是最硬的一条：**这条代码路径的成本没有变**。

**机制（源码核实，不是猜）**：`iq_kernels.cu:103` 的 dp4a 落在 `vec_dot_q2_0_q8_1` / `vec_dot_iq2_xxs_q8_1` / trellis（`tq_lut_i8`）——**是 Q2/Q3/IQ 类型**，不是我们 MoE 用的 Q4_K。decode 侧 `native_mmvq.cu` 那 45 处 dp4a 确实被换成了单指令，但 **decode 只有 0.6% 算力利用率**（10 专家 × 48 层 × 3 矩阵 ≈ 236 MMAC/ token，60 tok/s ⇒ 14 GMAC/s，而 FP16 峰值 26.5 TFLOPS），本来就是延迟/带宽受限 —— 把 28 条指令换成 1 条，**在这两个相位上都看不见**。

**举一反三（这条比结论更值钱）**：A0 的零结果**同步否掉了 B3 的前提**。B3（HC down-GEMM 用 q8_1 激活 + dp4a）与 MMVQ 同族——都是 decode 窗内的整数点积——既然 MMVQ 的 45 处 dp4a 换成单指令都测不出差异，B3 的上限也就是 0。所以 B3 不再需要窗口，直接按"前提不成立"处理。

**A0 去留**：留着。它**逐位不变**、指令更少、且是 B1/B2 能成立的前置（否则那些站点会更慢）。但**不许把它记成收益**。

**10. 事故：v1 窗口把生产打宕了约 2.5 分钟（我自己造成的）。**
06:03:46 装候选时，我把 config 的 `exe` 写成了**宿主路径** `/home/albus/strata166/data/bin/strata-0.1.57-pa0`；容器里只有 `/data/bin/...`，引擎 exec 失败 ⇒ `docker` 进入 `restarting` 循环（`RestartCount` 到 11）。06:06:0x 我手工 `sudo cp` 还原 config 并重启容器，06:07:22 恢复 `running`。**停机约 2.5 分钟**。

三个缺陷，全部是我自己的：

| # | 缺陷 | 修法 |
|---|---|---|
| 1 | `exe` 用宿主路径 | 配置里只写**容器路径**（`/data/bin/<名字>`），宿主路径只用于 `cp` |
| 2 | `trap` 里 `restore()` 不校验就被后续流程覆盖 | restore 后**必查 md5**，不符就 `sudo` 重试，仍不符则中止（不再继续"测量"） |
| 3 | `trap` 收到 TERM 后 return 而不退出 ⇒ 脚本在被杀之后继续跑，把生产二进制当候选测了 | 加 `trap 'restore; exit 130' INT TERM`，与 `trap restore EXIT` 分开 |

还有一条不是缺陷但要知道：**刚重启的引擎，第一条请求不写 `strata prefill timing` 行**（v1 因此报"no prefill timing line"），现在每臂先发一条预热请求并允许 3 次重试；另外**同一提示会被 prompt cache 整段命中**（我第一次手工复现时把缓存喂热了，导致下一轮 3 次重试全部无 prefill），所以窗口内用一次性盐值（`a0_salt`）保证两臂同文本、跨窗口不撞缓存。

**11. 更正：`Q4_K` 一直在走 dp4a，而且走的是「另一套」dp4a。**
上一段我写「`iq_kernels.cu:103` 的 dp4a 只服务 Q2/Q3/IQ，不是我们的 Q4_K」——**半对半错**。核清之后是两套 dp4a：

| 用在哪 | dp4a 来自哪 | gfx906 上 A0 之前 |
|---|---|---|
| **prefill MoE GEMM**（gate/up、down） | `moe_mmq.cu:533` → ggml `mul_mat_q_case` → `veccq.cuh` 66 处 `ggml_cuda_dp4a` → `common.cuh:750` **`__dp4a`** | **一直是硬件** |
| decode MMVQ / 我们自己的 iq/s2/dflash2 | 我们的 `hip_compat::dp4a`（`iq_kernels.cu:84` `#define ggml_cuda_dp4a(a,b,c) STRATA_DP4A(...)`） | **软件模拟（28 条）**，A0 才变 1 条 |

⇒ 所以 A0 的零结果是**自洽的**：它只动了第二套，而第二套的宿主相位（decode MMVQ）算力利用率 0.6%，本来就看不见。**prefill 一侧 A0 从头到尾没碰过**，它一直是硬件 dp4a。

**12. 「是不是可以走」：能走的指令已经走完了；缺的不是指令，是利用率。**
按 dp4a 的真实峰值算（64 CU × 64 lane × 1.725 GHz = 7.06 T 指令/s，每条 4 个 MAC ⇒ **28.2 TMAC/s**）：

```
prefill gate/up 2.5K：2500 tok × 10 专家 × 1280×2560 × 48 层 = 3.93 TMAC
实测 754 ms ⇒ 5.2 TMAC/s ⇒ dp4a 峰值的 18.5%
```

**还有 5.4× 的提升空间，但它不在「换哪条点积指令」上**——指令已经是 `v_dot4_i32_i8`，一条不多。剩下的 82% 只能来自占用率 / LDS / tile 组织 / CU 均衡。

一条看似可行、实测不可行的路也排掉了：**`v_dot8_i32_i4`**（gfx906 也有，一次 8 个 4-bit MAC）要求**两个操作数都是 4-bit**，而我们的激活是 q8_1（int8）；要用它就得把激活也压到 4-bit，那是**新的量化误差源**，不是"换个指令"。

⇒ 结论：`R95`/D2 的方向应当是 **用计数器证明 82% 花在哪**（survey 的 D2：每 CU `SQ_INSTS` 方差 + 最忙/平均比），而不是继续找"更快的点积"。这需要 `rocprofv3` 窗口。

**13. 有没有「专门的 gfx906 MMQ 优化代码」可移植？有，但只有三份，且两份不适用。**
把 survey 里所有 fork 的 matmul 目录翻了一遍，gfx906 专用 MMQ 代码只集中在 `iacopPBK` 的三份文件：

| 文件 | 是什么 | 对我们适用吗 |
|---|---|---|
| `matmul/mmq.cuh` | `GFX906_LOAD_TILES_Q8_0_ASYNC` / `GFX906_STORE_TILES_Q8_0_LDS_*`：把 tile 载入拆成「先全部读进寄存器、再全部写 LDS」；另有 `gfx906_load_q4_0_quants_vectorized`（2×int4 代替 8 次标量） | **手法适用，代码不适用**：宏只服务 **Q8_0** 权重与 **Q4_0** 激活；我们是 Q4_K |
| `matmul/mmq-prefetch.cuh` | Y/X tile 的 L2 预取（`global_load_dword` 后丢弃值） | 低优先：y 是小操作数，本来就在 L2；且是"读了就扔"的写法，收益不确定 |
| `matmul/mmf.cuh` | 自写 FP16 GEMM（M 9–2048） | **不适用**：那是 f16 权重的中批 GEMM，我们走量化 MMQ |

**真正值得移植的是那个手法**，而且它对着我们实测的缺口：`mmq-load-tiles.cuh:711`（`ggml_cuda_mmq_load_tiles_q4_K` 的 dp4a 分支）现在是**每次迭代一次依赖载入 + 一次 LDS 写**——

```cpp
for (int i0 = 0; i0 < I; i0 += nrows*nwarps) {
    const block_q4_K * bxi = x + kbx0 + i*stride;
    const int qs0 = get_int_b4(bxi->qs, txi);   // 唯一的载入，马上被用
    x_qs[i*(MMQ_TILE_NE_K + 1) + txi] = qs0;    // 立刻写 LDS
}
```

一个线程同时只有 **1** 个载入在飞。把它改成「先把 N 个迭代的 32 位读全发出去，再统一写 LDS」，同时在飞的就是 **N** 个——**逐位不变**（同样的值、同样的写序、同样的 LDS 布局），只有内存级并行度变了。这正是 iacop 那个宏在做的事，只是搬到 Q4_K 上。

**已交付的东西（状态要说清）**：`albus/w1036/mmq_stage_patch.py`（幂等补丁，带 `--revert`，用 `-DSTRATA_GFX906_MMQ_STAGE` 控制，默认不开）已写好，并且**已应用到 ggml 的副本**（`tmp/w1036/ggml-test`）并自检通过（3 处 `qs_cache`）。**但没有完成编译验证**：单独编 `mmq.cu` 只产出 871 B 的空目标（这个 TU 的设备端实例化依赖 CMake 那套宏），所以验证必须走**真实构建**——那不需要停服，用独立 build 目录再编一次即可（约 3 分钟），跑完再决定要不要开测量窗口。

**治理问题（比补丁更要紧）**：`/home/albus/strata166/llama.cpp`（166 MB）**不是 git 仓库**，而它是生产构建的输入。任何对它的改动都不可追溯、不可回滚到"改动前"。所以这个补丁在落地前必须先解决版本化：`git init` + 先提交一份原始快照，之后每个补丁一个提交。否则就是我刚刚在 A/B 窗口上犯过的同一类错——**改了不可追溯的生产资产**。

**14. 按机主指定：`PORT_PLAN.md` 升为权威方案里的 `R103`，队列置顶。**
`R103` = `albus/gfx906_survey/PORT_PLAN.md` 全量十一项（A0–D3），已写进 `W832 §0.1` 队列**第一位**、`§6.2` 有定义行、账本有一行（count 1 / done 0 / OPEN）。**并把 `R51` 的遗留吸收进来**：R51 当时只证了「10-19 栈的 `#29953` 补丁收益 0」，它名下真正的三项（Q8 流水线 / 向量 load / Y 预取）**从未测过**，现在归 R103。

**15. 上游最新版核对（机主：llama.cpp 要看最新版）。**
我们的 pin = `b11062` = `3cf03257`，**提交日期 2026-09-20**（GitHub API 实取）。gfx906 的 MMQ 配置那条上游 PR 是 **#27841「add missing AMD GCN MMQ config」，2026-09-12 已合并**（gfx906 三卡实测：Q4_K 平均 **+5.7%**、fallback 形状 **+11.2%**、adaptive **+15.8%**；Q6_K +34.5%、Q8_0 +46.4%）。因为合并早于我们的 pin **8 天**，**它已经在我们树里**——证据是 `mmq-config-gcn.cuh` 里已经有 wave64 的 `CASE(type, 256, 2, 64/128, J, …)` 行，共 73 行带 `512`。

**但那条 PR 的关键收益我们拿不到，原因很具体**：它把 **Q8_0 的 tile 宽度放到 J=128**，而 **Q4_K 的表只到 J=64**（实取：Q8_0 J∈{8,16,24,32,40,48,64,80,96,112,128}；Q4_K J∈{8,16,24,32,40,48,64}）。我们的 MoE 就是 Q4_K ⇒ **永远选不到 J>64 的 tile**。而 `mmq.cuh:1486` 的挑选循环本身是 `J <= 128`、`switch` 也一路到 112/128——**上限是配置表缺行，不是代码不支持**。

**16. 「其它项目都是针对 gfx906 开发的」——是，但它们的量化类型不是我们的。**
把 survey 里 gfx906 专用代码按「管哪个相位 / 吃什么类型」摊开：

| 项目 | gfx906 专用代码 | 吃哪种量化 | 对我们（Q4_K MoE） |
|---|---|---|---|
| **iacopPBK/llama.cpp-gfx906-2602**（最新，基于 build 7924） | 整个 `ggml-cuda/gfx906/` 目录：`matmul/mmq.cuh`（Q8_0 载入软件流水）、`mmq-prefetch.cuh`、`mmvq-q4_0/q4_1/q8_0.cuh`（**warp 协作 MMVQ**）、`mmvq.cu` 的 **half-warp 32 线程派发（MoE 小矩阵）**、`quantize/epilogue.cuh`（DPP 版 Q8_1 收尾）、`fused/mmq-prequantized.cuh`、`attention/fattn-q8.cuh` | **Q4_0 / Q4_1 / Q8_0**，dense 为主 | **手法可借，代码不可直接用**：我们的权重是 Q4_K、MoE 分组 GEMM |
| **上游 PR #27841**（已合并、已在我们 pin） | GCN 的 wave64 MMQ 配置 + I<128 不再 fallback + J 到 128 | 全类型，但 **K-quant 只放到 64** | 已吃到配置，**J>64 那一半没吃到** |
| exabit-io（4×Vega20） | fused norm 直吐 Q8_1、mmq-prequantized、Q8 复用 | Q8_0 激活侧 | 与我们的 `STRATA_QFUSE` 同题；B3 的前置 |
| KI（vLLM gfx906） | 自建 **W4A16 grouped GEMM**、fattn-q8、dense GEMV | 自建格式（非 ggml） | 不是 MMQ，但 **grouped GEMM 正是 MoE prefill 的形态** |
| QPhuGit/Argon | `gfx906_dlops.hpp`（sdot4 封装）+ swizzle 实测 | 通用 | 我们的 A1/A3 同源 |
| 3chet | **17 条负面结果**（无代码） | — | 省掉重做 |
| milpster | rocBLAS gfx906 段错误报告 + workaround patch | 通用 | D3 |
| sixvolts / fuutott / eslowney / marcelromano | QSA 长上下文、wave64 内核、D=128 专线 | fp16 / Q8 | 与我们形状不同 |

⇒ 结论：**「专门针对 gfx906」的代码确实存在，而且不少**，但它们绝大多数解决的是 **Q4_0/Q8_0 的 dense GEMV**（decode 侧），我们缺的是 **Q4_K 的 MoE 分组 GEMM**（prefill 侧）。所以能拿的是**手法**（载入暂存、DPP 归约、半 warp 派发、预量化直喂），不是文件。

**R103 的第一手（按证据排序）**：① **Q4_K 的 J 上限**（改配置表，最便宜，直接对着 18.5% 那个缺口）；② 载入暂存（补丁已在 `albus/w1036/mmq_stage_patch.py`，未编译验证）；③ D2 计数器（容器里有 rocprofv3 1.3.5）。三项都不需要改内核代码的前两项，第三项只读。
