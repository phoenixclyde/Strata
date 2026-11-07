## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0） |
| 3 | **config** | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；**args 37**；**env 9** |
| 3a | args | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `..._MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` |
| 4 | 健康 | `/health` ok、`loaded:true`、**restarts=0**、StartedAt `2026-11-05T11:58:52Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；`VmLck: 0 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` + `docker restart strata166-407` |
| 8 | 本轮改动 | **生产零改动、零重启**（只在 `build-tab/repacktest/` 做独立 bench）；三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `0856e14e` · 跟踪 `origin/gfx906/mi50` · 落后 0 / 领先 16 · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **0**；重启 **0 次**；停机 **0**。引擎/config md5 前后相同。

## 四、进度 + 队列

**202 条 / 已结 127 / 62.9%**；主线 **174 / 127**；死块池 **0/28**。
队列：**R91 → R96 → R95 → R94 → R89 → R46 → R49 → R50**。

---

## 五、按你说的「继续走」：做了真 A/B，不是推断

把 mx 的 repack 路径**实际编译出来跑**了：

| 步骤 | 做法 |
|---|---|
| 摆头文件 | `ref/mx` 8 文件 → `build-tab/repacktest/ggml-cuda/repack/`；用 `llama_b12110`(ggml 0.29) 的 `common.cuh`/`mmq.cuh`/`unary.cuh` 补齐相对 include |
| 唯一 stub | mx 的 `ggml_cuda_q8_1_cache_acquire` 在 0.29 树没有 → stub 成 `cached=nullptr, hit=false`（该 host helper bench 根本不调用），`probe.cu` 编译 RC=0 |
| 数据 | host 端内联 `repack_q51`（照抄 `repack-common.cu:285`，Q5_1 三平面就是拷贝）生成 repacked 权重，stride = `repack_gcn_nbytes` = 1,239,040 B |
| kernel | `mmq_gemm_repacked<true, 2, 4, GGML_TYPE_Q5_1>`，grid=(10, tiles)、block=(64,4)，参数照 `mul-mat-id.cu:325` 填 |
| 编译 | `hipcc -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906 -DGGML_USE_HIP` → `BUILD_RC=0` |

产物：`/home/albus/strata166/build-tab/repacktest/repack_bench.cu` + 同目录 `repack_bench`，可复跑。

## 六、实测结果：repack 四档全不快

同形状 16 专家、Q5_1 down 640×2560，canonical 臂 = 现役 `kq_bench`：

| rows/expert | canonical | repacked | 比值 |
|---:|---:|---:|---|
| 32 | **0.238 ms** | 0.543 ms | 慢 **2.28×** |
| 128 | **0.540 ms** | 0.557 ms | 慢 3% |
| 320 | **1.243 ms** | 1.464 ms | 慢 18% |
| 1024 | **3.489 ms** | 3.582 ms | 慢 3% |

repacked 在 320 行的 5 次重跑：1.465 / 1.463 / 1.464 / 1.469 / 1.419 ms（稳定）。**四档一致、无一处更快**，尤其小行数（正是 R95 关心的 2K 短档）差最多。

**与前几轮证据同向**：W997 反汇编（主 GEMM 地址指令仅 16–18%）、W998 代理实验（Q8_0 平面布局净慢）、W997 外网核对（mx README 无 +84% 表，gfx906 fork 公开 PP16384 +14.1%）。

**局限如实记**：mx kernel + 0.29 头混搭、激活用全零标准 `block_q8_1`（只计时）、mx 自带的松散 grid 有少量空转；不是完整生产移植。但四档同向、且与三条独立静态证据一致，判否稳健。

## 七、R86 正式结案

**R86 = DONE_NEG，不做生产移植**（P278 留可复现路径与数据）。按你「测完有实际数据才能做判断」的规矩，这次是实测完才关的。

**方案 V3.7 队列前移**：**R91（dot8 六阶段）→ R96（gate/up 融合）→ R95 → R94 → R89 → R46/R49/R50**。

## 八、下一步

1. **R91-P1**：float→int4 量化器（每 32 值 scale + Σa 写进 block 头），零停服单测、与 CPU 参考逐元素一致；
2. **R96**：llama.cpp #31188 的 CUDA gate/up+GLU 融合能否映射到 HIP `mul_mat_q_tab` 的源码判断；
3. **R94 质量门**（KL/top-1）并行，纯测量不占 GPU。

（报告已过 `report_lint`：12 字段 PASS。）
