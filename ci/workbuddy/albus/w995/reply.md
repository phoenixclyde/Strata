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
| 8 | 本轮改动 | **生产零改动、零重启**（只改账本/方案/审计索引）；disk = build = running 三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `0856e14e` · 跟踪 `origin/gfx906/mi50` · 落后 0 / 领先 16 · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **0**；重启 **0 次**；停机 **0**。引擎/config md5 前后相同。

## 四、进度 + 队列

**196 条 / 已结 120 / 61.2%**；主线 **168 / 120**；死块池 **0/28**。
队列：**R86 → R91 → R96 → R95 → R94 → R89 → R46 → R49**。

---

## 五、上网核对了两条，都改变了判断

| 来源 | 内容 | 对我们的作用 |
|---|---|---|
| Q8_1 激活复用的机制说明 | llama.cpp **每个 prefill chunk 只量化一次激活，整层所有投影复用**那块 Q8_1；"量化开销在任何超过几个 token 的 prompt 上都是舍入误差" | 直接指向 R87 可能本来就已实现 |
| 一份完整的 Q8_1 + dp4a 移植实测 | 做完、验证正确后 **tg128 差异 <1%、在噪声内**；原因是 DRAM 流量由权重主导，激活只 ~8 KB 且命中 L2 | 说明即便硬做，收益也大概率测不出来 |
| llama.cpp **PR #31188**（2026-10-30 合并） | MoE 的 gate、up 两次 matmul + GLU 融进**一次** `mul_mat_q` 启动；宣称 prefill 最高 +17.2%，但**原文明确写"无对照数据、不能归因"**，且 CUDA-only | 正对 R95 的 gate/up（20.6%），立为 **R96**（先做源码可行性，不认领 17%） |

## 六、R87 判否（不是凭印象，是源码 + 实测）

**源码**：`prefill.cpp:5010` 注释逐字——「the layer's activations as q8_1 rows in expert order … **each token quantized once** and written to its K rows」，对应 `mmq::quantize_scatter`。⇒ **我们早就有激活复用**，R87 的前提不成立。

**实测**（`STRATA_PREFILL_TIMING`，量化落在 `gather` 相位）：

| 长度 | gather | GPU timeline | 占比 |
|---|---:|---:|---:|
| 2K | 9–24 ms | 3,668 ms | **0.2–0.7%** |
| 16K | 64 ms | 19,543 ms | **0.3%** |

R87 自定判据是"每请求量化总时间 <1% 则不做" ⇒ **DONE_NEG**。P272 记录数据，外网两证作为交叉印证。

## 七、审计索引回写（上一轮发现）

`AUDIT_INDEX.md` 的「`build.ninja` 不可重生成」已改为 **W994 更正**：挂对 `/ref=llama_b12110` + 透传 GPU 后全量 configure/build RC=0、产物 md5 复现生产。保留的规矩写在同一行：单 TU 仍走 `ci/build.sh` 三条逐字命令，全量重建以 md5 为验收门。

## 八、R86 的现状（下一手）

| 项 | 状态 |
|---|---|
| `kq_bench` | **已按 r32 同款 flags 重编**，可跑（需 `STRATA_MMQ_KQ=1`） |
| 新基线 | Q5_1 down [640,2560]：**1.246 ms / 6.73 TMAC/s**（W944 旧构建 1.53/5.47 ⇒ +23%）；Q4_K gate/up 2.29–2.57 ms 持平 |
| repack 参考树 | `/home/albus/strata166/ref/mx` 在，但 `ggml-cuda/` 下**没有 repack 代码**（sparse clone 没带全）⇒ 需先补齐参考实现 |
| 判据 | canonical vs repacked 单内核 **<20% 判否、≥40% 才动生产**；`prefill_mmq_tab_test` 逐位 |

Q5_1 仍是供给率最低的一档（6.73 TMAC/s，峰值约 25%）⇒ repack 的空间没有被 0.9.0 吃掉。

## 九、下一步

1. **补齐 mx 的 repack 参考实现**（或按 W944 断言自己写 60 行 repack kernel），接进 `kq_bench` 的 B 臂；
2. 两臂各 n≥10，按 2×CV 判；不过 40% 就不动生产；
3. R96 同时做源码可行性（#31188 的 CUDA 融合能否映射到 HIP 的 `mul_mat_q_tab`）；
4. R94 质量门并行。
