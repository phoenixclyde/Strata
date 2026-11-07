**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0） |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`（chunk 臂已自动回滚，`--prefill` 回 `auto:16384`）；exe=`/data/bin/strata-0.1.56-090`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-05T16:45:25Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（host **16,473,712 KB**）；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_235103 /data/strata-huihui-ud-iq4_xs.json` + `docker restart strata166-407`（本轮**未动用**，`cfg_apply` 自动回滚） |
| 8 | 本轮改动 | 生产零改动（1 次试装已自动回滚，终态 md5 `e62685e6…`）；引擎/镜像未变；disk = build = running = `eea5ea37…` |

**二、主线** gfx906/mi50 @ f013f9b6 · tag `mi50-0.2.10-r32-20-gf013f9b6` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行。
**三、本次落生产** 改动 0；重启 1 次（试装后自动回滚）；停机约 1 分钟；回滚件未用；代码面 1 提交 `f013f9b6`（2 文件 +9/−1，chunk 实测入仓 + BUNDLE 证据路径）。
**四、进度** 263 条 / 已结 183 / **69.6%**；队列 R95（`P333` 归因待事件）→ R94（相对门）→ R91 → R89 → R46 → R49 → R50。

---

## 五、一个臂，把 chunk 的价钱和 91 ms 的机制一起买了

W1015 我把 91 ms 的机制写成「复用等待（双缓冲可解）」，但那只是读注释的推论。本轮用最小代价测它：同一个 2K prompt，把 `--prefill` 从 `auto:16384` 改成 `1024`，请求就要过 **2 个 chunk**，于是每层的 `d2h_sync`（`pinned_ring.hpp:105-114`，`cudaMemcpyAsync` + **`cudaStreamSynchronize`**）跑 **96 次**而不是 48 次，而它的调用点就是 `prefill.cpp:4663`（`host grouping` 相位从 `prefill.cpp:4655` 起算）。

| 量 | chunk 16384（1 chunk） | chunk 1024（2 chunks） | 比值 |
|---|---:|---:|---:|
| prefill@2000 | **513.65 tok/s** | **406.07** | **−20.94%**（band 0.86） |
| TTFT | 4.096 s | 5.489 s | **+34.0%** |
| `host grouping` | 91 ms | 105–121（中位 **108**） | **×1.19** |
| `wait copy` | 37 ms | 364–521 | **×10–14** |
| `dequant` | 161 ms | 398–464 | ×2.6 |
| gemm gate/up | 816 | 1227–1267 | ×1.52 |
| gemm down | 510 | 764–802 | ×1.53 |

**`auto:16384` 从此有了价位：砍到 1024 是 21 个点。**

## 六、三个机制模型全被这个臂否掉，包括我自己昨天写的那个

1. **每层一次 sync 的固定延迟**：层-趟数翻倍，`host grouping` 只 91→108（×1.19，不是 ×2）⇒ 否。
2. **拷贝 3.2 MB**：跨 chunk 拷贝量也翻倍，同样没翻倍；且绝对值 0.5 ms 比 91 ms 小两个数量级 ⇒ 否。
3. **建表随 T 增长**：16K（T=16375）只有 **64 ms**，比 2K 的 91 ms 还小 ⇒ 否。

⇒ `host grouping` 是**每请求 90–110 ms** 的量，机制未知。W1015 的「复用等待、双缓冲可解」**撤回**（`P331 → DONE_NEG`，原推论见 `prefill.cpp:4656-4657` 的注释）；在 `P309` 的两个事件（launch 前后量 `busy/phase`）落地之前，**不许动这块代码**——否则就是拿一个没验证的机制去改最敏感的一段。

## 七、外网：profiler 这条路在 166 上走不通

ROCm 侧测「同步阻塞时间」有现成仪器：`rocprofiler-sdk` 的 `rocm_sync_nanoseconds`（按 HIP 同步 API 累计 host 阻塞）、`rocm_kernels_nanoseconds`、`rocm_memcpy_nanoseconds`。但文档写明 **Requires ROCm 7+**，我们是 ROCm 5.7/6.x + `HSA_OVERRIDE_GFX_VERSION=9.0.6` ⇒ **该仪器不可用**。结论：只能靠树内事件（`P309`），不要指望外部 profiler —— 这条写进方案，省下一次「先装 profiler 再说」的弯路。

## 八、举一反三：否掉自己假设的臂，比支持它的臂值钱

这一轮 6 分钟、零代码改动，换来的是：**一个会让我写错代码的方向被删掉**。如果按 W1015 的机制直接去写双缓冲，改的是 `ids/slot/src/bounds` 四处复用关系——**改错不报错、只是偶发算错**，这是最贵的一类 bug，而且它只值 2.9%。

所以判据再加一条：**机制假设必须先有一个「能证伪它的最小实验」**，才允许进代码；写不出证伪实验的机制，只能记「待归因」。本轮 `chunk 1024` 就是这样一个实验：它同时给出 chunk 的价位（21 点）、否掉三个模型、并且零风险（自动回滚）。

## 九、门与同步

`plan_lint` A–F PASS；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py:139` 全 PASS；`ledger` 29 项、`param_pair` 15 处与上轮持平（旧债）；六件权威件双侧逐字节。本轮新增：`§6.5 回写·W1016`、`P332`（chunk 1024 定价）、`P333`（三模型全否）、`P331` 撤回、`ci/prefill_phases/W1016_chunk1024_raw.txt`（8 条相位行入仓）、`BUNDLE` 的 R95 行改成「机制未定位」。
