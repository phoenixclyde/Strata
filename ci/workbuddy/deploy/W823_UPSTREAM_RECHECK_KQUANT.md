# W823 上游复核（2026-10-29）：换到 K-quant 之后，还该不该升到 0.2.7

> 结论：**不升。** 上游没有针对我们这条路（x86 Qwen 引擎 + K-quant 专家 + HIP/gfx906）的新东西；
> 0.2.7 唯一有量的两项，一项本机拿不到（PLE 常驻），一项是正确性修复。
>
> 与 W820（10-28）的区别：那次评估的基线是 **IQ4_XS**，这次基线是 **UD-Q4_K_XL + `STRATA_MMQ_KQ=1`**，
> 所以必须重新查"0.1.52 有没有改 K-quant 这条路"，而不是复用旧结论。

---

## 1 上游到底到哪了（GitHub API 实查，10-29 21:5x）

| 对象 | 最新 | 说明 |
|---|---|---|
| Release | **v0.2.7**（10-27 14:54，30567 字节正文） | 之后**没有新 release** |
| Tag | **v0.2.7.1** | 有 tag 无 release；引擎 **0.1.53** |
| main | **0.1.53** | 最后提交 `2026-10-28 08:11`，此后 **37 小时无提交** |
| x86 Qwen 引擎 | **0.1.52**（= v0.2.7） | 我们：**0.1.49.2** |

0.2.5 / 0.2.6 的正文自己写了：Qwen 引擎 **0.1.50**，且 0.2.6「nothing in them changed」。
0.2.5 那条 "prompt chunk sizes follow what the PC holds" 是 **NVIDIA <16 GB** 的 DeepSeek 分支，不是我们。

## 2 v0.2.7.1 有什么：127 提交 / 132 文件，引擎面 32 个全是别人的

按顶层目录：`metal` 35、`src` 29、`tools` 18、`tests` 15、`packaging` 13、`docs` 5、`strata_control` 5、
`strata_cli` 4、`include` 2、根文件 4。

引擎面 32 个文件里：**29 个 `src/dsv41/*`（DeepSeek）**、`metal/*`、`include/strata/core/nv_defaults.hpp` +
`src/core/nv_defaults.cpp`（NVIDIA 默认值 + 新测试）、`src/kernels/cpu/portable.cpp`、
`src/prefill/moe_fused_iq.cu`（+15 行，内容是 **GB10/sm_121 的瓦片阈值**，`dev_info().s121` 只对 compute 12.1 生效）。

⇒ 对 gfx906 / x86 Qwen：**零改动**。

## 3 关键一节：0.1.52 有没有改 K-quant 这条路（我们现在跑的就是它）

逐个文件比对 v0.2.4.2 ↔ v0.2.7：

| 文件 | 规模变化 | 对 HIP/gfx906 的实际影响 |
|---|---|---|
| `src/prefill/mmq_kq_loader.cpp` | 124 → 124 行，**+-0** | **逐字节相同**（K-quant MMQ 的装载与判据） |
| `src/prefill/moe_mmq.cu` | 687 → 769 行，+-88 | K-quant 的 `case GGML_TYPE_Q4_K/Q5_K/Q6_K/Q5_1` 未变；新增 trellis 类型 147-149（我们不用）；新增融合 `swiglu_quant` 被 `#if !defined(__HIPCC__) && defined(STRATA_EXPERIMENTAL_SM60)` 挡住，`swiglu_quant_ok()` 在 HIP 上直接 `return false` |
| `src/kernels/cuda/native_mmvq.cu` | 3276 → 3913 行，+-673 | **673 行全部在 `#if !defined(__HIPCC__)` 内**（`native_mmvq_il_pf_kernel` 族 + Q4_K/Q5_K/Q6_K 的瓦片表）；HIP 侧只多一个空桩 `void native_mmvq_il_pf(int) {}`。Traits 里只加了 `[[maybe_unused]] TYPE` 常量 |
| `src/core/expert_cache.cpp` | 807 → 902 行，+-95 | Windows/NVML（`STRATA_VRAM_FREE=device`）+ `STRATA_EXPERT_NIBBLE` 的 seal 检查；Linux 无关 |
| 45 个引擎文件的补丁（compare API） | — | 含 `HIP` / `__HIPCC__` / `gfx906` 的**新增或删除行 = 0** |
| `docs/QUANTS.md` | 178 → 178 行 | **逐字节相同**（质量/速度表没变） |
| `docs/AMD_HIP.md` | 1123 → 777 行 | 只是重写/搬移；gfx906 章的技术内容不变：attention 两个开关**仍默认关**、两卡 `--pipeline-windows 2`（我们单卡） |

**这就是不升级的核心依据**：我们 10-29 刚把生产换成 K-quant，而 K-quant 的装载器两版逐字节相同、
MMQ 分派未变、解码路径的改动全被 `!__HIPCC__` 挡掉。

## 4 唯二有实质内容的两项，一项拿不到、一项不是速度

### 4.1 `STRATA_PLE_AUTO_RAM`（0.2.7 新增，默认开）——本机必被拒

`include/strata/core/ple_residency.hpp` 的准入逐字：表 + **引擎还要填满的竞技场** + headroom，
全部对"两者分配**之前**的可用内存"衡量；未知遥测/未知表大小/未知竞技场大小一律不放行。

我们换权重后：表 26.8 GiB + 竞技场 **71.7 GiB** + headroom ⇒ 约 **105 GB**。
本机常态 `MemAvailable` 60 余 GB（ComfyUI 一旦加载模型就是 10 GB 级）。
⇒ 拒绝，回落 0.2.6 的 direct 读（**与今天完全一致**）。所以"升级能拿到 PLE 那 16.5-30.6%"在本机不成立。

### 4.2 正确性修复（不是速度）

- **#3602**：PLE reader 不再永久等待（配 `STRATA_PLE_CHECK=1`）。
- **#1503**：会话缓存不再串用别人的 K/V。
两条都需要故障注入或长跑才能验证，不能算进"升级的收益"。

## 5 我们自己的 A/B 已经测过（可以外推，但要标前提）

W820 第一轮：0.1.49.2 / 0.1.52 / 0.1.49.2 交错，同一语料（IQ4_XS）：

| tokens | A | B(0.1.52) | A2 | B 是否在 A/A2 漂移带内 |
|---:|---:|---:|---:|---|
| 1453 | 3.46 s | 3.99 s | 4.13 s | 是 |
| 2498 | 4.92 s | 5.14 s | 5.19 s | 是 |
| 4568 | 8.46 s | 8.75 s | 8.74 s | 是（差 0.01 s） |

那次测的是 IQ4_XS。**外推到 Q4_K_XL 的前提是"K-quant 路径未变"**——正好由 §3 证明。
（那次解码臂不可用：同二进制 A vs A2 差 38%，漂移比效应大，未采信。）

## 6 举一反三：三个不升级就能测的东西

1. **`STRATA_ROUTE_TAIL_SKIP` 该更划算，但要量 KL。**
   0.2.7 的 `generate.cpp:11024-11065` 写明：默认开，除非"≥90% 专家在 GPU 缓存"（`STRATA_TAIL_SKIP_MAX_CACHED`，默认 90；
   HIP layer-split 时 60）。换权重后我们的覆盖率从 **40%（9873/24576）降到 30.7%（7551/24576）**，
   按上游 2×R9700 的曲线（IQ3_S：44-52% 时 +6..15%，60% 时约 0），30% 应该更划算。
   上游给的代价是 **KL 0.003-0.006**——我们从未量过。→ 建议做 teacher-forced KL（7 vs 0），两次重启。
2. **`STRATA_FILE_CACHE_OLD_RULE` 绝对不能设 0。**
   `AMD_HIP.md` 逐字：gfx906 **故意**保留旧规则，因为 MI50 上内核回收 HMM 追踪的 arena 时 ROCm 队列会被挂起
   （#1752，KevinX8：文件层停止冲刷页缓存后 prompt **46 → 360 tok/s**）。`=0` 把这个保护拿掉。
   这与我们 W810 的"55.43 GiB 竞技场冲掉 26.8 GiB PLE 表"同源 ⇒ **设计取舍，不是 bug**。
3. **`STRATA_DENSE_MMQ` 在 0.1.49.2 里已存在**（`strings` 命中 2 次）。
   `--compat-bf16` 把 195 个 Q8_0 小投影转成了 BF16；如果这条能接住它们走 MMQ，可能补回一部分 prefill。
   **未验证**，属候选，不动生产。

## 7 判定与触发条件

**维持 0.1.49.2（v0.2.4.2）。** 什么时候重新评估：

- 上游 release 正文出现 `gfx906` / `K-quant` / `MMQ` / `prompt` 的**速度**条目（不是正确性）；
- `main` 的 `src/kernels/cuda/*` 出现**不在 `!__HIPCC__` 守卫内**的改动；
- 我们要跑 Q5_K_XL / Q6_K_XL（需 `-DSTRATA_Q6K_EXPERTS=ON` 重建，那是"换档"不是"升级"）；
- 0.2.7 的 #3602 / #1503 在我们这里真的复现（PLE reader 挂死、K/V 串用）。

## 8 数据与脚本

- `albus/w823/{diff_mmvq.py,scan_mmvq.py,diff_rest.py,scan_hip_patches.py,fix_model_name.py,reg_w823.py}`
- 落盘对照件：`albus/w823/{mmvq_old.cu,mmvq_new.cu,mmvq.diff,cache_old.txt,cache_new.txt,amdhip_new.txt,older_new.txt,cmp_files.json}`
- register：**P146** 追加本轮复核；新增 **P150**（model_name/aliases，FIXED）、**P151**（FILE_CACHE_OLD_RULE=0，REJECTED）
