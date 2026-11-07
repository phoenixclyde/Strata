# W1046 · R103 后续方案入权威并开工：B3 候选 + k8v4 dot8 原型

**一、生产容器（10 字段，2026-11-07 19:4x 只读）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 · StartedAt `2026-11-07T09:56:22Z` |
| 2 | 运行中引擎 | `strata-0.1.57-attn` · md5 `3b758f88ddad25cdad236be267810a9e` · 43,452,008 B（**未换件**） |
| 3 | config | md5 `3dde880125925d785a49da69fa1ebdfb` · `exe=/data/bin/strata-0.1.57-attn` · args 38 / env 10（**未改**） |
| 3a | args 明细 | `--serve` `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE(_MAX)` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` `STRATA_GFX906_ATTN_DP4A=1`（10 项未动；`STRATA_HC_DOWN_DP4A` 只在候选中，生产未设） |
| 4 | 健康 | `/health` ok · `max_context 262144` · restarts=0 · `could not map` / `ERR the K/V could not` 全文计数 0 |
| 5 | 资源隔离 | `memlock=-1:-1` · `VmLck 0 kB` · `ulimit -l` unlimited |
| 6 | 显存 | used 33,618,952,192 / total 34,342,961,152 ⇒ **VRAM free 724,008,960 B（0.67 GiB）**；expert cache **8301 槽 / 24.23 GiB**；prompt path borrows 2609 槽 (7.62 GiB)；`elastic K/V 16384 of 262144` |
| 7 | 回滚件 | `/data/bin` **56 件**；上一版 `kvg`（`a85743d7…`）、`b12180`（`d24f8293…`）在册；rollback = 停容器 → `cp` 回 `tmp/w1044/cfg_w1044b.bak` → 起容器（≈45 s） |
| 8 | 本轮改动 | **生产引擎/config 零变更，disk = build = running 三方一致**；只新增候选 `hc4`、源码分支与本机工具/文档；**重启 0 次 / 停机 0 s / 装机 0 / 回滚 0** |
| 9 | ROCm | 10.1.0 · HIP 7.16.26323 · clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；生产源码树 `pr/k10` @ af797b90（`gfx906/lcpp-k10`，领先 2 / 落后 0，脏 0 行）。新候选 `gfx906/hc-dp4a @ 179bd6b5` 已推 `origin`，pre-push `ROUND_GATE: PASS`；未合入主线。上游本轮未换基线。

**三、本次落生产** — **零**：引擎未换件、config 未改字节。**重启 0 次 / 停机 0 s / 装机 0 / 回滚 0**。B3 的干净计时与数值窗口需要另批停机；本轮所有构建、自检和原型均零停机。

**四、进度** — **473 条 / 已结 382 / 80.8%**（本轮 +6：`P523`–`P526` + `R109`/`R110`；`R108` 重复项并入 `R91` 后收口）。队列：**R109（B3 候选判门 → A1 → A5 死派发前提）** → **R110（k8v4 PV-dot8 真实模型数值门）** → R106 → R107（15 轮未审）→ R105 → R95…

## 1. 方案已经改了什么

- `deploy/W832_OPT_PLAN_V2.md §0.1` 的唯一队列已把 **R109/R110** 置顶，并写明单变量、默认 off、数值/任务/2×CV 与停机边界；§6.5 有本轮回写块。
- `albus/gfx906_survey/PORT_PLAN.md` 已追加 W1046 执行更正，不再把 B2 当成「还可再拿 2–4%」。
- `deploy/REBUILD_RECIPE.tsv` 已登记 `hc4` 的源码、llama pin、构建目录、md5 和大小。

## 2. B2 是死路径，不是下一笔收益

源码核实：`src/kernels/cuda/qsa_pattn.cu:35` 的开关在 HIP 构建下不会启用，`src/prefill/prefill.cpp:4420` 的 prompt 选择在 `qsa_prompt_attn_batch` 拒绝后回退既有 decode attention 路径。W1044 装机的 DP4A 已在这个路径上拿到 prefill 收益。因此 B2 与 B1 在生产上合并，**不再对 `qsa_pattn.cu` 做无效移植**。`P435` 也已追加这层更正。

## 3. B3 已实现，但只到「候选可判」

- 分支 `gfx906/hc-dp4a @ 179bd6b5`，只改 `src/kernels/cuda/fused_gr.cu`；新增默认 off 的 `STRATA_HC_DOWN_DP4A`。
- 真实落点是 Q8_0 HC down：staging 时每 32 个 FP32 激活量化一次，权重 int8 × 激活 int8 走 DP4A，最后乘 `d_weight×d_activation`；inject 行仍走 BF16，原内核保留作 off 臂。
- 候选 `strata-0.1.57-hc4`：md5 `df33d3a60eb4c8515b6f34e090af7e40` / 43,675,416 B，**未装机**。
- 零停机实测：`gr_parity` **0 failures**；`fused_gr_bench` off/on 均 **0 differing**，非 Q8 对照 hash 不变；单 TU ISA `v_dot4_i32_i8` **720**、`v_dot8_i32_i4` **0**。
- Q8 相对 BF16 的 `mixed` rel-RMS 从约 **0.0009 → 0.0012**，证明新增量化改变数值；cold 子模式两臂都 timeout/dumped core，**没有干净性能结论**。
- 外证支持「量化必须摊销」而不是「dot4 必然快」：wiki-gfx906 实测 hot-loop QDQ 2.00 TOPS < FP32 5.95，复用后 dot4 21.7 TOPS；MI50/vLLM 的 gfx906 FA 也用 Q8_0 Q + dot4，并强调 fp32 scale/accumulator。

## 4. k8v4 能不能走 dot8：能试 PV，QK 不行；目前质量门未过

- ROCm/LLVM 文档明确 `v_dot8_i32_i4 = i4x8 × i4x8`，**两个操作数都是 int4**。所以 k8v4 的 int8 K 不能直接走 dot8；QK 若硬用，K/Q 都要再降 int4，已不属于当前 k8v4 面。
- V 的布局见 `include/strata/kernels/kv_q4.hpp:550`：32 值一 fp16 scale + 16B nibble；减 8 后是 signed int4。硬件 helper 在 `include/strata/kernels/gfx906_dot.hpp:38`，有效 dot4 对照在 `include/strata/platform/hip_compat/strata_hip.h:237`。
- 独立原型 `albus/w1046/k8v4_pv_dot8_proto.cu`：P×Vscale 按 8-cell 组量化 int4，V 按 8 个 cell 打包；CPU/GPU 逐点对齐。2000 reps：**6.511 → 4.391 µs，1.483×**；合成 rel-RMS **6.23%**、max-abs 0.1004。
- 这个计时把 P 量化/打包放在外面，是**性能上限**；6.23% 也不是模型 KL。结论仅是「值得用真实模型 P/V dump 做数值门」，**不是可装机**。初版误按 int4×int8 写的原型数据已作废。

## 5. 下一步执行顺序

1. **R109/B3**：先修/绕过 cold bench 子模式故障；独立停机窗口做同 exe off floor、on 数值 + 长生成/needle、隔离 HC 与引擎交错 A/B。只在数值过门且收益 ≥ 当次 2×CV 时提装机。
2. **R110**：从生产一次只读 dump 取真实 P、Q4_0 V 与 scale，测 P(int4) 的 logits/KL/top-1 和任务级影响；若真实误差不可接受即 DONE_NEG，不为 1.483× 上限继续烧窗口。
3. B3 有结论后才做 A1 exact DPP；A5 必须先证明 k8v4 调用面并解除 `STRATA_EXPERIMENTAL_SM60` 死派发；A2/A3 逐开关，A4 最后逐 TU。

## 数值技能状态（照实抄录；本轮未执行其三臂停机段）

| 组件 | 状态 |
|---|---|
| 三臂 argv 生成（`quant_quality.engine_args()` 逐字打印比对） | 已实测 |
| 预检（两臂 exe md5 / config md5 / set.ids.json / numpy / stray 容器=0） | 已实测 PASS |
| 比对器（同输入 0、σ=1e-3 扰动约 4.33e-03） | 已实测（合成数据自测） |
| 三臂整跑 + KL/top-1 出数 | **未执行，等停机授权；本技能停机段是设计稿，不是实录** |

另修 `P526`：`attn` 配方 note 的历史「未装机」曾让 `recipe_check` 跳过在产件；已修正并实测 `[ok] attn md5=3b758f88…`。`audit_scope §A` 仍为 **15 轮连续未审**，已同步 R107，不冒充解决。

产物：`albus/w1046/`（本报告、`port_b3.py`、`build_b3.sh`、`verify_b3.sh`、`k8v4_pv_dot8_proto.cu`、`land_*.py`、源码检查文本）；166 `tmp/w1046/` 保留 bench/parity/ISA/原型日志。
