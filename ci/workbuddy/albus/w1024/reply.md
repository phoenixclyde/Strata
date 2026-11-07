**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` / `strata-gfx906:0.2.11-101`（image `2e7539eeb76b`） |
| 2 | 运行中引擎 | `strata-0.1.57-001`，md5 `5e63174dbd7cc04e5fa1b5fc455b2a73`，42,947,088 B |
| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43`；exe=`/data/bin/strata-0.1.57-001`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-05T18:46:29Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（`--ulimit memlock=-1:-1`）；host **16,473,712 KB**；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | `strata-0.1.57-001`（现役）、`strata-0.1.57-002`（b12129 试版）、镜像 `0.2.10-101`；`ci/rollback.sh --exe … --apply` |
| 8 | 本轮改动 | **生产零改动、零重启**（只读）；git 分支对齐 1 次（`exp/R90-080`）；离线构建 1 次（b12129+#31047，未部署）；disk = build = running 三方一致 |
| 9 | **ROCm 版本** | 打包 `.info/version` = **10.1.0**；HIP 运行时 **7.16.26323-0000000**（`hipconfig`）；clang **24.0.0git**；`ROCM_BUILD=7.14.0-gfx906+20260802001858` |
| 10 | **llama.cpp 版本** | **b11062** = `3cf03257f219afbe7334045ff7c6a06ac68c627d`（2026-09-20）；树 hash `6feee589…`（2824 文件 / 166,037,690 B） |

**二、主线** gfx906/mi50 @ 372106ed · tag `mi50-0.2.11-r33-8` · 落后上游 0 / 领先 71 / merges 0 · `origin == HEAD` · 脏 0 行。
**三、本次落生产** 引擎 0 次；镜像 0 次；**重启 0 次**；停机 0 分钟；回滚件未动用；代码面 0 提交。
**四、进度** 289 条 / 已结 209 / **72.3%**；队列 R95（`P335`）→ R94（相对门）→ R91 → R89 → R46 → R49 → R50，另 `P359`（b12169 分派层）。

---

## 五、容器内到底是什么版本（`docker exec strata166-407`，不是宿主、不是台账）

| 项 | 值 | 取法 |
|---|---|---|
| ROCm 打包标记 | **10.1.0** | `cat /opt/rocm/.info/version` —— 该目录**只有这一个文件**，7 字节 |
| HIP 运行时 | **7.16.26323-0000000** | `hipconfig --version`；库名就是 `libamdhip64.so.7.16.26323-0000000` |
| 编译器 | **clang 24.0.0git**（ROCm LLVM `e3dd2f54`） | `hipcc --version` |
| 构建标识 | **7.14.0-gfx906+20260802001858** | 容器 env `ROCM_BUILD`（自建 gfx906 分支） |
| rocprofv3 | 1.3.5（git `af82d0ab`） | `rocprofv3 --version` |
| **llama.cpp** | **b11062 = `3cf03257f219afbe7334045ff7c6a06ac68c627d`** | `/src/BUILD-IMAGE.json` 的 `llama_cpp` / `llama_cpp_build` |
| llama.cpp 树 | 2824 文件 / 166,037,690 B / `6feee58927d5f1efd38e72bbc1db061d`，**无 `.git`** | 容器内 `find … md5sum \| md5sum` |

三个 ROCm 数字不同不是笔误：这是**自建 gfx906 树** —— `.info/version` 是打包字符串，`ROCM_BUILD` 是构建 ID，HIP 运行时才是组件版本。它们没有一个是"官方 ROCm 7.x"的常规编号，所以任何报告都必须写清取的是哪一个。

## 六、rebase 全程复核：树逐字节等价，64/64 全保留

判据不是"看 git log 觉得对"，而是**比对两棵树**：

| 检查 | 结果 |
|---|---|
| rebase 版 vs merge 版 | `git diff 85297483 22abb0c0` → **输出为空**（零丢失、零多余） |
| 提交数 | merge 版 66 = **2 个 merge commit** + 64 实质；rebase 版 64 ⇒ **64/64 全保留** |
| 线性与同步 | `merges=0`、`behind=0`、`ahead=71`、`origin == HEAD`、`dirty=0` |
| 上游引擎 TU 有没有被我们盖掉 | `src/prefill/prefill.cpp`、`gemm.cu`、`gemm_w16_parity.cu` 相对 `9f7d977d` **零改动** ⇒ 上游修复完整保留 |
| tag | `r33-2..8` 都在主线祖先链上；`r33-1`（`85297483`）是 **merge 版快照**、ORPHAN，但正是上面那条等价性判据的基准 |
| 分支 | `main` 已对齐；`exp/R90-080` 曾落后主线 5 且 **0 独有提交** ⇒ 本轮 `reset --hard 372106ed`；`exp/lcpp-b12129` 保留 1 个独有提交（b12129 移植） |

**三个发现，都改了或记了**：① `exp/R90-080` 是个"假实验分支"（无独有内容），已对齐；② `r33-1` 是孤儿 tag，保留作基准但要在 message 里写明；③ **W1023 的归因错了**（见下一节）。

## 七、最新 llama.cpp 是 b12169，但它不能直接换

- 最新 tag **`b12169` = `3ed7284f2d9e22b2d1a7d05c1416c00c5a9f0bc7`**，比 `b12129` 多 **40 个提交**；
- 这 40 个里碰 MMQ 的**只有 `69ee2ecc` = #31047**（6 文件、+230/−231），其余都是 vulkan/metal/opencl/webgpu/hexagon/server；
- **修正 W1023**：#31047 **不在** b12129 里，而在 b12129..b12169 之间 —— 上次那 −4% 是"**没有**这个优化"的版本，不能写成"抄不到 1.23×"。

把 #31047 单独打到 b12129 上（patch 干净应用，dry-run rc=0）后编译，**只剩 1 个错误**：

```
src/prefill/moe_mmq.cu:505:73: error: cannot initialize a member subobject of type
'const ggml_cuda_mm_id_tile_spec *' with an lvalue of type 'const int32_t *const'
```

`mmq_args` 的第二组字段被换掉了：`expert_bounds`（`int32_t*`）→ **`tile_spec`（`ggml_cuda_mm_id_tile_spec*`）**，`ncols_max` → `ntj`。spec 每条 16 字节 `{expert, col_low, col_high, padding}`，由 `mmid.cu` 的 helper 预计算，条数 = `ceil(n_tokens*n_expert_used/J) + n_expert`，并按 J 的 seam 对齐。

**这不是改签名，是改分派数据的形状**：`src/prefill/moe_mmq.cu:505` 自己构造 `mmq_args`，`p.bounds` 在显存里（`src/prefill/prefill.cpp:2252` 传入），要换 spec 就得在 device 端把「每专家列区间」按 J 切成「每 tile 一条」。`moe_mmq.cu:504` 的 `pick_J` 也要跟着 `ntj` 的语义重算。

## 八、为什么今晚不硬上

`tile_spec` 在 kernel 里是**直接解引用**（`mmq.cuh:1079` 等，无空指针分支），算错**不报错、只是结果错** —— 这是本项目最贵的一类 bug。可靠的做法是：

1. 在 `exp` 分支写 `bounds → tile_spec` 的 device kernel（参照 `mmid.cu:120-140` 的 seam 对齐，避免 D2H 同步）；
2. 先过**数值门**：48-token 贪心指纹与 b11062 **逐字节一致**；
3. 再谈速度，判据同 W1023：任一档超 2×CV 即回滚；
4. 收益预期不能外推：PR 自报 MI50 **Q4_0 mb64 1.23×**，我们的专家是 **Q4_K/Q5_K**，适用性必须实测。

工作量估 2–3 小时（含两轮编译 + 验证）。已记 `P359`，主线与生产都不受影响。

## 九、门与同步

`RELEASE_CHECK` **PASS**（10/10，pin 仍 b11062）；`plan_lint` A–F PASS；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py` 全 PASS；`ledger` 30 项、`param_pair` 15 处（旧债持平）；六件权威件双侧逐字节。本轮新增：`§6.5 回写·W1024`、`P357`（容器内版本）、`P358`（rebase 复核）、`P359`（b12169 分派层，OPEN）。
