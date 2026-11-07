## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `ae085365441381c438b56bcabcccf450`，42,924,432 B，`strata 0.1.56` |
| 3 | **config** | md5 `24d66f6a86d7b75f58015efa38d462d2`；exe=`/data/bin/strata-0.1.56`；**args 33 条**；**env 9 条** |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、restarts=0、StartedAt `2026-11-04T11:39:38Z`、max_context 262144 |
| 5 | 资源隔离 | `ulimit -l = unlimited`、`VmLck 28,125,140 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`VRAM free 882 MiB` |
| 7 | 回滚件 | 容器 `strata166-407.pre-210`、引擎 `strata-0.1.55w`、`ci/strata-ci rollback --exe strata-0.1.55w --apply` |
| 8 | 本轮改动 | 部署分支**零**；disk = build = running 三方一致（`ae085365…`）；实验分支 `exp/R90-080` 2 个提交（未合） |

## 二、主线

`gfx906/mi50 @ 55a1acd4` · tag `mi50-0.2.10-r30` · 上游 `ffa80d73` · 落后 0 / 领先 39 · 工作树脏 0 行。

## 三、本次落生产

改动 **零**；回滚命令 `cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 …/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`；本轮为测量重启 **1 次**（0.7.0 单跑），停机 **≈4.5 分钟**（脚本自动恢复）。

## 四、进度 + 队列

**176 条 / 已结 101 / 57.4%**；主线 148 / 101 / 68.2%；死块池 0/28。
队列：**R88-量** → **R86-A/B** → R87 → R46 → R91 → R93 → R72 → R81 → R79 → R80 → R63/R60/R64 → R49 → R50 → R30′；R90 转为"摘修复"。

---

## 一、版本地图（GitHub API 实查）

| 版本 | bump commit | 日期 | PR |
|---|---|---|---|
| **0.4.1（我们）** | `e6ab7c1a4` | **2026-09-22** | — |
| 0.5.0 | `7fe450e` | 2026-09-23 | #29333 |
| 0.6.0 | `d812350` | 2026-10-05 | #29997 |
| 0.7.0 | `620d222` | 2026-10-15 | #30603 |
| 0.8.0 | `8642541` | 2026-10-28 | #31309 |

**0.5.0 只比我们晚一天**——我们不是"落后一个版本"，而是正好停在 0.4.1 末态，之后四个月一条没吃。

## 二、MMQ 这条线：8 个提交，三个跟我们有关

| 日期 | commit | 标题 | 影响 |
|---|---|---|---|
| 09-25 | `e9f824d8` | `llama_prec_policy` + W4A4 (#24364) | `ggml_prec` 从这里进来 |
| 10-08 | `fc9ce6b9` | **fix MMQ out-of-bounds reads (#29953)** | **正确性修复，我们没有** |
| 10-09 | `8a1a9b51` | pass src1 precision to host helpers (#30168) | 我们 7 处补参的原因 |
| 10-19 | `4c1004c4` | cap Stream-K blocks (#30553) | 我们不走 stream-k |
| 10-23 | `1a24df16` | DP4A tile height assert (#30837) | 只加断言 |
| 10-25 | `c49edf09` | **fuse FFN gate/up + GLU (#29948)** | **0.8.0 的 `mmq.cuh` 就是它** |
| 10-29 | `eb4e244b` | RDNA4_M (#31373) | 只影响 gfx117x |

## 三、−6% 定位：**就是 fusion 那一次提交**

用中间版本 bisect（不是猜）：0.7.0 已有 `prec` + `J_best`，但**没有 fusion**。

| 点 | 树 | prefill（tok/s） |
|---|---|---:|
| A | 0.4.1 | **601.7**（3 次：601.74/604.28/599.17） |
| **C** | **0.7.0（`620d222`）** | **594.11** |
| B | 0.8.0 | **565.8**（3 次：568.41/552.15/576.82） |

**C 与 B 差 5.0%，C 与 A 差 1.3%** ⇒ 四个 minor 里对 gfx906 prefill 的**唯一负向改动就是 fusion**，其余合计约 1%。

硬证据对得上：**0.8.0 的 `mmq.cuh` 与 fusion 提交逐字节相同**（1659 行，diff 0）。

## 四、三条怀疑用源码排除了

- **GDN MMA**（新增 `gated-delta-net-mma`）：`select_gdn_mma_path()` 在 HIP 下要求 `CC_IS_RDNA3_5` 且 `n_tokens≥2048` ⇒ gfx906 直接走老路径；
- **RDNA4_M**：只对 gfx117x；
- **MUSA `__CUDA_ARCH__`**：与之无关。

## 五、该摘的一条：`#29953` 的越界读修复

```cpp
ids_dst:  ne_get_rows                    ->  ne_get_rows + J_best-1      // 补 J-1
src1_q8_1: + get_J_max()*sizeof(block)   ->  + src1_q1_padding(按 nthreads*sizeof(int) 上取整)
```

一个 J 宽的 tile 会**多读最多 J-1 列**。我们 0.4.1 没有这个修复，生产能跑说明越界落在 pool 余量里（未定义行为，没炸而已）。
而我们的 `moe_mmq.cu` 是**直接调** `mul_mat_q_case`，`xq`/`ids` 的尾部余量得自己保证——**下一步要核对**。

## 六、决定

**0.8.0 与 0.7.0 都不划算**（−5~6% / −1.3%），**留在 0.4.1**；要新基线的东西就按 `W961 §5` **摘单个修复**，首推 `#29953`。

产物：`deploy/W961_LLAMACPP_RELEASES_ANALYSIS.md`（版本地图 + 提交清单 + 排除依据）、`deploy/W962_BISECT_FUSION.md`（bisect 全过程）；账本 R90 仍 **INFLIGHT**；结案台账 40/40。
