## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0 基线） |
| 3 | **config** | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`（与开 debug 前逐字节相同）；exe=`/data/bin/strata-0.1.56-090`；**args 37**；**env 9** |
| 3a | args 明细 | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、**restarts=0**、StartedAt `2026-11-05T11:58:52Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；引擎 `VmLck: 0 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | 引擎 `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` 后 `docker restart strata166-407` |
| 8 | 本轮改动 | **净零**（`DEBUG_J` 开了又撤）；disk = build = running 三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `0856e14e` · 跟踪 `origin/gfx906/mi50` · **落后 0 / 领先 16** · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **0**（观测开关加→撤）；**重启 2 次**（开 1 + 撤 1），各 ≈45 s，**停机合计 ≈1.5 分钟**；回滚件同上。

## 四、进度 + 队列

**191 条 / 已结 115 / 60.2%**；主线 **163 / 115**；死块池 **0/28**。
队列：**R95 → R88 → R94 → R89 → R91 → R86 → R87 → R46**。

---

## 五、R95-1 结论：**J 恒为 64**，小专家只填了半个 tile

用 `STRATA_MMQ_DEBUG_J` 抓一次 2K 请求的全部 tile 选择：

| 项 | 值 |
|---|---|
| `pick_J` 调用次数 | **1,564**（48 层 × 专家×gate/up/down） |
| 选中的 J | **全部 64**，无一例外 |
| ncols（每专家 token 数） | min **4** / p50 **331** / p90 **742** / max **7680** |

源码：`pick_J` 从 8 到 128 步长 8 遍历、取"tile 数最少"的那个；但 gfx906 上 `ggml_cuda_mmq_get_config` 对 J<64 返回 `GGML_TYPE_COUNT`（不可用）⇒ **实际只有 64 及以上**。

**后果**：ncols=4 的专家也要跑一个 64 宽的 tile（填充率 6%）；16K 时 p50 ncols≈2,650 ⇒ 41 个 tile、填充率接近满。这与相位数据完全一致：gate/up 0.482（2K）vs 0.252 ms/tok（16K）。

## 六、长度曲线：单调收敛、**没有台阶**

| tokens | GPU timeline | ms/tok |
|---:|---:|---:|
| 2,056 | 3,668 ms | 1.784 |
| 3,058 | 4,805 ms | 1.571 |
| 4,056 | 6,519 ms | 1.607 |
| 6,058 | 8,730 ms | 1.441 |
| 9,058 | 11,949 ms | 1.319 |
| 12,057 | 15,384 ms | 1.276 |
| 15,757 | 19,543 ms | 1.240 |

平滑收敛到 1.24，**没有 wave 边界那样的台阶** ⇒ 不是"块数不够一波"，而是**tile 填充率 + 每专家固定成本（权重读/反量化/启动）随 token 数摊薄**。

## 七、R95-2 的三个候选（按可验证性）

| 候选 | 依据 | 做法 |
|---|---|---|
| **A. 让 J<64 可用** | 全部 J=64，ncols p50=331 但 p10 很小 | 查 `mmq_get_nbytes_shared` 与 gfx906 的 LDS 上限，看 J=32 是否只是被共享内存卡住；若是，缩小 tile 的 K 分块即可启用 |
| **B. 小专家走 small-M 路径** | ncols<64 的专家跑 64 宽 tile 是浪费 | 对 ncols<64 的组用 GEMV/小 M kernel（引擎已有点积核），按 `expert_bounds` 分流 |
| **C. dequant 融合** | 2K 时 dequant 0.125 ms/tok 是 16K 的 3.9× | 把反量化并入 GEMM 的 load 阶段，省一遍权重读 |

判据统一：2K/8K/16K 三档，`gemm gate/up` 相位 ms/tok 降 ≥15%，decode 不掉。

## 八、下一步

1. **先做 A 的可行性判断**（读 `mmq_get_nbytes_shared` + gfx906 的 64 KB LDS）——只读源码，不改；
2. 若 A 可行 ⇒ 加一个 J=32 实例 + 按 ncols 选择（需要一次编译，约 10 分钟/TU）；
3. `DEBUG_J` 已撤（1,564 行/请求的日志不能留在生产）。
