## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0 基线） |
| 3 | **config** | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；**args 37**；**env 9** |
| 3a | args 明细 | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` **`STRATA_PREFILL_TIMING`（本轮新增）** |
| 4 | 健康 | `/health` status=ok、`loaded:true`、**restarts=0**、StartedAt `2026-11-05T11:46:53Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；引擎 `VmLck: 0 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | 引擎 `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` 后 `docker restart strata166-407` |
| 8 | 本轮改动 | **1 项**：`STRATA_PREFILL_TIMING=1`（观测，+0.8% TTFT 在噪声内）；disk = build = running 三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `0856e14e` · 跟踪 `origin/gfx906/mi50` · **落后 0 / 领先 16** · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **1 项**（开观测开关）；**重启 1 次**（≈45 s），**停机 ≈1 分钟**；回滚件同上。

## 四、进度 + 队列

**190 条 / 已结 114 / 60.0%**；主线 **162 / 114**；死块池 **0/28**。
队列：**R95 → R88 → R94 → R89 → R91 → R86 → R87 → R46**。

---

## 五、R88-1 完成：不用改代码，引擎自带分相位计时

`STRATA_PREFILL_TIMING` 是既有开关（`prefill.cpp:2981`），每请求打两行：26 个 GPU 相位 + 主机分解。开启代价：TTFT 4.106 vs 4.074（+0.8%，band 2.0%）⇒ 在噪声内，可常驻。

**实测两档（同一配置、冷读）：**

| | 2K（2,056 tok） | 16K（15,757 tok） |
|---|---:|---:|
| GPU timeline | **3,668 ms** | **19,543 ms** |
| wall | 3,683 ms | 19,665 ms |
| **主机缝隙** | **15 ms** | **122 ms** |
| 每 token | **1.784 ms** | **1.240 ms** |
| host staging | 375 ms | 508 ms |

⇒ **那 1.3 s 不是主机缝隙**（缝隙只有 15 ms），而是**首块每 token 更贵**。

## 六、差额去哪了：小批 GEMM，不是预取、也不是 CPU 池

每 token 成本对比（ms/tok）：

| 相位 | 2K | 16K | 倍数 | 折算到 2K 请求的贡献 |
|---|---:|---:|---:|---:|
| **gemm gate/up** | 0.482 | 0.252 | **1.91×** | **+473 ms** |
| **gemm down** | 0.299 | 0.160 | **1.87×** | **+286 ms** |
| **dequant** | 0.125 | 0.032 | **3.9×** | **+191 ms** |
| **wait copy** | 0.071 | 0.005 | **14×** | **+136 ms** |
| qsa attn | 0.123 | 0.216 | 0.57× | **−191 ms**（小 prompt 更便宜） |
| gdn / qsa proj / out proj / recurrence | ≈ 0.37 | ≈ 0.36 | 1.0–1.1× | ≈ 持平 |

合计 ≈ **+1.12 s**，与 3,668 − 2,056×1.240 = 1,118 ms 吻合。

**结论**：`gemm gate/up + down` 一项就占 68% 的超额。原因指向"每组专家的行数太少"——2K prompt 分到每个专家只有几十行，tile 利用率低；dequant 同理（没摊薄）。`wait copy` 14× 说明小批时每层同步占比高。

这也解释了为什么之前的实验全部落空：**借用量、CPU 池、pcie-frac 都改不到这条路径**。

## 七、方案改写（R88 拆成 R95）

| 项 | 旧 | 新 |
|---|---|---|
| R88 | 首块重叠/预取 | 保留，但降级：缝隙只有 15 ms，没有东西可重叠 |
| **R95（新）** | — | **小批 GEMM 效率**：2K 时 gate/up 1.91×、down 1.87×、dequant 3.9×、wait copy 14× |

R95 的候选（按可行性）：

1. **MMQ 的 J/`ncols` 选择**：小行数时是否选到了大 tile 配置（`get_J_max` 家族，`mmq.cuh`）——这是最可能的单点；
2. **dequant 与小批 GEMM 融合**：0.125 ms/tok 是 16K 的 3.9×，说明去量化没有被摊薄；
3. **`wait copy`**：小批时每层一次同步，改成跨层预取（原本 R88 的机制，挪到这里才有意义）。

判据：2K/8K/16K 三档同测，GEMM 相位 ms/tok 降 ≥10% 且 decode 不掉。

## 八、下一步

1. **R95-1 读码**：0.4.1 的 `mmq.cuh` 里小 ncols 的 J 选择逻辑，确认 2K 时实际选了多少 J（这决定 tile 利用率）；
2. 若 J 选大 ⇒ 加一个按行数选 tile 的规则（对应 R23 的 `wave_rows` 思路，但对象是 MoE grouped GEMM）；
3. R94 质量门并行做（纯测量）。
