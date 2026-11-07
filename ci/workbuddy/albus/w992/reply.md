## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0 基线） |
| 3 | **config** | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；**args 37**；**env 9** |
| 3a | args 明细 | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、**restarts=0**、StartedAt `2026-11-05T11:58:52Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；引擎 `VmLck: 0 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | 引擎 `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` 后 `docker restart strata166-407` |
| 8 | 本轮改动 | **零改动、零重启**（纯源码核实）；disk = build = running 三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `0856e14e` · 跟踪 `origin/gfx906/mi50` · **落后 0 / 领先 16** · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **0**；重启 **0 次**；停机 **0**。回滚件同上。

## 四、进度 + 队列

**191 条 / 已结 115 / 60.2%**；主线 **163 / 115**；死块池 **0/28**。
队列：**R95 → R88 → R94 → R89 → R91 → R86 → R87 → R46**。

---

## 五、R95-A 否决：J=64 不是 GCN 的缺失，是 K-quant 的设计下限

查了四张架构表（`ggml/src/ggml-cuda/mmq-config-*.cuh`）：

| 架构表 | Q4_K 可用的 J |
|---|---|
| GCN（gfx906，我们） | **64 / 128** |
| RDNA3 | **64 / 128** |
| CDNA | **128** |
| Ampere | **128** |

⇒ 所有架构上 Q4_K 的 tile 宽度都**从 64 起**。也就是说，我上一轮设想的"GCN 少了一行 J=32"**不成立**——加表行也没用，因为 K-quant 的 MMQ 内核根本没有 J<64 的实例。

**结论：候选 A（启用 J<64）作废**，不再花时间编译。

## 六、这意味着什么

2K 时 gate/up 的 1.91× 不是"选错了配置"，而是**结构性的**：

- 每个专家 64 宽的 tile 是固定粒度；
- ncols 分布 min 4 / p50 331 / p90 742 ⇒ 尾部大量专家只填了 64 宽 tile 的一小部分；
- 16K 时 p50≈2,650，同样 64 宽，但每个 tile 都是满的。

换句话说：**同样的内核、同样的 tile 宽度，只是 2K 喂不满**。这也解释了长度曲线的平滑（无台阶）——填充率随 token 数连续变化。

## 七、剩下两条路（都要动代码）

| 候选 | 机制 | 预期上限 | 代价 |
|---|---|---|---|
| **B. 小专家分流** | ncols<64 的组不走 MMQ，改走 GEMV/小 M 内核（引擎已有点积核） | 只看尾部：若 20% 的调用 ncols<64，可省它们浪费的 60–90% 时间 ⇒ **2K gate/up 约 −10~15%（≈100–150 ms）** | 代码 + 编译，约半天 |
| **C. dequant 融合** | 2K 的 dequant 0.125 vs 16K 0.032 ms/tok（3.9×），把小批反量化并进 GEMM 的 load | **−0.19 s**（占 2K 总时 5%） | 代码 + 编译，风险中等（要保证 bit-exact） |

**我的判断**：B 的收益更大但对路由/边界改动多；C 收益确定、边界更窄。**建议先做 C，再做 B**。

## 八、下一步

1. **C 的可行性核实**（只读）：`dequant` 相位在 `prefill.cpp` 里的调用点，确认它是对"专家权重"还是"激活"做的、能否与 load 合并；
2. 若可行 ⇒ 改一处 + 编译一个 TU（约 10 分钟）+ `cfg_apply` 三档判据；
3. 同时把 R94（质量门 KL/top-1）排上——它是 R90 的欠账，纯测量。
