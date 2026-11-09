# W1055 回执：dot4 软路径毒化探针（前提证伪）+ wave64 硬件盘点 + R116 预算 PASS

**一、生产容器（10 字段，本轮结束时）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 |
| 2 | 运行中引擎 | `strata-0.1.57-hc4b` · md5 `0533074826258d5f96c4b65bc0ad33df`，未换件 |
| 3 | config | md5 `8d234fa38261abbee0328c80416d6835`（W1049 装机态原样）· `exe=/data/bin/strata-0.1.57-hc4b` · args 38 / env 13，未改 |
| 3a | args 明细 | 38 项逐字未动（`--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow`） |
| 3b | env 明细 | 13 项逐名未动（`HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` `STRATA_GFX906_ATTN_DP4A=1` `STRATA_HC_DOWN_DP4A=1` `STRATA_HC_DOWN_DP4A_MAX_T=6` `STRATA_GFX906_ATTN_LDS_PAD=1`） |
| 4 | 健康 | `/health` → `{"status": "ok", "max_context": 262144}` · restarts=0 · StartedAt `2026-11-08T05:14:12Z` |
| 5 | 资源隔离 | `ulimit -l` unlimited · `memlock=-1:-1` · `VmLck 0 kB` |
| 6 | 显存 | VRAM free 849,211,392 B（0.79 GiB）；expert cache 8301 槽 / 24.23 GiB；borrows 2609 槽 (7.62 GiB)（本轮只读） |
| 7 | 回滚件 | `attn`（`3b758f88…`）+ `kvg`；备份 `tmp/w1052/cfg_pv_pre.bak`；rollback = `cp` 回备份 json 并冷重启（≈45 s） |
| 8 | 本轮改动 | **零落生产**：换件 0、config 改 0、**重启 0 次 / 停机 0 s**、装机 0、回滚 0；探针构建全在 scratch（build-masterp），`strata_hip.h` 已还原（md5 `80c3f447` 与备份一致） |
| 9 | ROCm | 打包 .info/version 10.1.0；HIP 7.16.26323；clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；生产树 `pr/k10`，领先 0 / 落后 0 / 脏 0 行，上游本轮未重算。新证据件：`albus/w1055/`（毒化探针三件套 `probe_build.py`/`probe_counts.py`、`wave64_audit.md` 子代理件、`pv_budget_r116.py`）。

**三、本次落生产** — **零**：装机 0 / **0 分钟停机**；**重启 0 次 / 停机 0 s**。证伪性结论意味着**不需要改任何代码**——生产已是 100% 硬件 dot4。

**四、进度** — **528 条 / 已结 439 / 83.1%**（+3 条 `P578`–`P580`）。队列：**R116（预算 PASS → 下一道门=微基准）** → R74 → R91 → R85（手段序 R46 > R64 > R60）→ R89 → R95 → R86 → R101（详见 `W832 §0.1`）。

## 1. dot4 软路径清零——毒化探针证伪「还有软路径」（P578）

你的前提「有部分代码路径走软 dot4」在**二进制层面被证伪**，用的是比 grep 强一个量级的毒化实验：

1. 软实现的唯一定义点 = `strata_hip.h` 的 **unsigned `strata_dp4a` 重载**（4 次逐字节乘加；int 重载在 gfx906 上是 `__builtin_amdgcn_sdot4` 硬件）。
2. 给 unsigned 重载插 `0xdeadbeef` ISA 标记（`asm volatile` 不可优化掉），重建全部 TU。
3. **28/28 TU 反汇编 `marker=0`**——没有任何调用点解析到软重载 ⇒ 生产 dot4 100% 硬件：`native_mmvq 37,464 / iq_kernels 44,746 / dflash2 21,600 / fused_gr 720 / attn 384` 条 `v_dot4_i32_i8`。
4. 之前看到的 `v_mad_u32_u24`/`v_mad_i32_i24`（合计 ~360 条）**都不是 dot4**：attn 那条反汇编实证是 **LDS 偏移乘法**（`v1*s31+v6 → ds_write`），mmq 的 195 条是 **IQ4XS dequant 的合法 24 位乘**（每实例 1 条，`native_mmvq_wave_kernel<IQ4XS,…>`）。头文件已还原（md5 一致），生产未动。

**方法论教训**：`grep ISA 指令名 ≠ 找到软路径`——`v_mad_*` 是通用 24 位乘指令；要证明「某重载没被用」，毒化标记是唯一干净的手段（与 P500 的取样面教训同一族）。

## 2. wave64 有没有硬件级专属代码？——**有，4 组**（P579）

子代理全扫（55 处 `THREADS/32` 逐点表 + 指令用法清单，`albus/w1055/wave64_audit.md`）+ 我复核可达性：

| 组 | 内核 | wave64 硬件机制 |
|---|---|---|
| 最成熟 | `native_mmvq_wave_kernel` | **width-64 `__shfl_xor` 蝶形归约** + `64%T` static_assert + 实测 R 表 + env 开关 |
| 次之 | `router_top10_wave_kernel` | 64-lane argmax 蝶形（gfx906 默认路径，逐位一致论证完整） |
| 3 | iq_kernels `row_dot64` | W64 模式（64 列一行点积） |
| 4 | fused_gr | down-split / up-fast 跨 lane 归约 |

- **没有 DPP / ds_swizzle 指令用法**——全树 0 处；DPP/permlanex16 都在被 `!STRATA_HIP_GFX906` 排除的 wave32-RDNA 代码里（gfx906 上不可达）。
- **R52 的「wave32 假设」证伪**：~55 处 `THREADS/32` 全部落在 `strata_hip.h` 的「逻辑 32-lane 半波」契约内（width-32 shuffle / 半波 ballot 恰好把 wave64 切成两个逻辑 warp，gfx906 上按设计正确）。R52 收窄为剩运行期实测（活跃波槽占比 + 波槽清单）。
- 唯二脱离契约的 `__match_any_sync(0xffffffffull)`（topk.cuh:51 / qsa.cuh:240）在 **`src/split/` 子树（独立 CMake，gfx906 引擎不构建 ⇒ 不可达）**，且代码自注已按 HIP 64 位掩码处理——无险，登记备查。

## 3. R116 误差预算 PASS（P580）：int8 比int4 好 17.7×

`pv_budget_r116.py`（22 记录重放，同 R112 取样面）：

- **P(int4)×V(int4)** rel_rms 4.5951%（R112 判否基线，逐位复现）；
- **P(int8)×V(int8-exact)** rel_rms **0.2603%**、max_abs 0.038 —— spec 预测 ~16×，实测 **17.7×**；
- 误差远小于 DP4A 当年采纳时的 q 误差 1.3%（P454）与同噪地板 KL 0.0411（P461/P470）⇒ **数值门过（有条件）**；代价 = V 读流量 2×（int8 vs 4-bit nibble）。
- **下一道门**：微基准（同访问面 >1.3× 才谈 OPT 位，R116 预注册）。

## 5. 边界与纠错留痕

- 毒化构建只重建了 scratch 的 .o；**生产二进制与在产容器全程未动**（health ok、md5 三方一致）。
- P518 的 per-TU 归属更正（34/195/87 的 TU 映射与总数保留，归属按函数级反汇编修正）——记在 P578。
- 波槽占比的运行期实测（R52 ③④）未做——留 R52。
- 落点可复核：`albus/w1055/probe_build.py:1`（毒化+还原）、`probe_counts.py:1`（28 TU 计数）、`wave64_audit.md:1`（子代理全扫）、`pv_budget_r116.py:1`（R116 预算）、账本 `deploy/PROGRESS.tsv`（`P578`–`P580`）、方案 `deploy/W832_OPT_PLAN_V2.md` W1055 段。
