# W775delta W17 ---- gfx906 开关面全景清点（"还有多少参数可以扩展"）

日期 2026-10-11 12:38 ｜ 源 = 0.1.42 镜像（`strata-gfx906:0.1.42`）只读扫描，**未停生产** ｜ 工作区 `D:/workbuddy_space/strata_ws/`

> 触发：机主问「还有多少参数可以扩展到 gfx906 上」。判据 = 不再用「文档说哪个架构」，改用**两条硬证据**：(1) 源码 `getenv("STRATA_*")` 全量（存在面）；(2) `strings <binary>` 命中（**该字面量真被编进本机镜像** = 编译期可达）。

## 1 方法（可复现）

**【审计后定死 canonical】** 桶口径以 **`deploy/tmp/_w17_gen.py`**（**本件的生成脚本**）为准：
- `D` = `DBG|TEST_|_TRACE|_DUMP|_TIMING|_STATS|_PROFILE|GOLDEN|SELFTEST|_CHECK$|WATCHDOG|RSS_|POOL_TRACE|PIPELINE_LOG|PIPELINE_DEBUG|PREFILL_HELP|DUMP_FIRST|SNAPSHOT_FULL|STATE_HASH|STARTUP_UNBUFFERED|MEMORY_LIMIT`。
- **两处曾被误置的边界（2026-10-11 审计 #2/#7 指出，已改归）**：`EXP_MODE`（实验专家布局的**模式选择器**，改行为）由 D 改归 **X**；`_GATE` 结尾只有带 `DBG` 的算 D（`DBG_CPU_GATE`），`LFUSE_GATE`/`SPEC_PROB_GATE` 是**功能门** => 归 **X**。
- 旧脚本 `_w17_final.py`（DIAG 含 `_GATE$`）会给出 **X=129**；**已被 `_w17_gen.py` 取代**，本件一律用后者（X=132）。
- 桶是**名字筛上界**，非定论；逐条守卫判定 = `W750` 的 `W17a`。

```
# 1) 存在面：二进制字符串 ∪ 源码 getenv
docker run --rm --entrypoint bash strata-gfx906:0.1.42 -lc \
  'strings /src/build-906/strata | grep -oE "STRATA_[A-Z0-9_]{2,}" | sort -u'
docker run --rm --entrypoint bash strata-gfx906:0.1.42 -lc \
  'cd /src && grep -rhoE "getenv *\\( *\"STRATA_[A-Z0-9_]+\"" src include serve | sed -E "s/.*\"(STRATA_[A-Z0-9_]+)\"/\\1/" | sort -u'
# 2) 编译期可达：二进制字符串表是否含该名（不含 => 死在 #if 里）
# 3) 守卫栈：容器内 python 逐文件维护 #if/#elif/#else/#endif 栈，记录每个 getenv 的外层条件
```

**关键校验（决定整表对错）**：若某名只出现在 `#if !defined(__HIPCC__)` 里却**仍**在二进制字符串表 ==> `__HIPCC__` 未定义。
实测：`#if !defined(__HIPCC__)` 族 7 个**全部不在**二进制；`#if defined(__HIPCC__)` 族 8/9 **在**二进制
==> **`__HIPCC__` 确实定义**（gfx906 走 hipcc），"排除"判定成立。

## 2 层叠计数（现算）

| 层 | 数 | 判据 |
|---|---:|---|
| env 存在面（二进制 ∪ 源码 getenv） | **352** | 镜像实扫 |
| CLI 长选项（粗测：`generate.cpp` 184 + `serve` 60，并集 226） | **226** | 源码 grep。**[!] 口径缺陷（审计 #6）**：`serve` 侧命令带 `head -60` => **60 是截断上限非真值**；`generate.cpp` 侧 184 含 `--native-`/`--yarn-` 等**片段 token** => 226 **既非上界也非真值**，仅作数量级 |
| register 已登记（env 面文本命中） | **56** | 其中 ADOPTED 26 已上生产 |
| **未登记 env** | **296** | 352-56 |
| ├ 编译期排除（仅源码、不在二进制） | **34** | 死在 `#if` 里 |
| └ **编进本机镜像** | **262** | `strings` 命中 |
| &nbsp;&nbsp;&nbsp;├ M 多卡/peer/pipeline/驻留面（单卡不触发） | 73 | 名字筛 |
| &nbsp;&nbsp;&nbsp;├ D 诊断/测试/跟踪（不改行为或只测量） | 40 | 名字筛 |
| &nbsp;&nbsp;&nbsp;├ C CPU 宿主专家面 | 18 | 文件+名字筛 |
| &nbsp;&nbsp;&nbsp;└ **X 单卡 GPU/引擎逻辑（实质候选池）** | **132** | 剩余 |

**一句话答案：存在面 352 个 env + 226 个 CLI；其中 262 个 env 真编进了本机镜像，再刨掉多卡(73)/诊断(40)/CPU(18) => 剩 132 个是"单卡 GPU/引擎逻辑"候选池。**

## 3 编译期排除（34 条，仅源码、不在二进制）

- `STRATA_ATTN_PRE75`  (src/kernels/cuda/qsa_decode_attn.cu)
- `STRATA_BF16_TC`  (src/prefill/gemm.cu)
- `STRATA_DEFERRED_REGISTER`  (src/core/expert_source.cpp)
- `STRATA_DF_PDL`  (src/kernels/pdl_parity.cpp)
- `STRATA_FETCH_PVM`  (src/core/expert_source.cpp)
- `STRATA_FILE_RELEASE`  (src/core/expert_source.cpp)
- `STRATA_GDN_CHUNKED`  (src/prefill/gdn_rec_parity.cu)
- `STRATA_GDN_KEYHEAD`  (src/prefill/kernels.cu)
- `STRATA_HIPBLASLT_VERBOSE`  (src/prefill/gemm.cu)
- `STRATA_HIP_ADAPT_KERNEL_COPY`  (src/program/generate.cpp)
- `STRATA_HIP_ROUTER_OLD`  (src/kernels/cuda/router_top10.cu)
- `STRATA_KV_HOST_DMA`  (src/prefill/prefill.cpp)
- `STRATA_MMVQ_IL_ROWS`  (src/kernels/cuda/native_mmvq.cu)
- `STRATA_MTP_PRIORITY`  (src/core/mtp.cpp)
- `STRATA_MULTI_BLOCK_ARGMAX`  (src/kernels/cuda/verify_kernels.cu)
- `STRATA_PA_FAST`  (src/kernels/cuda/qsa_prompt_attn.cu)
- `STRATA_PF_BK64`  (src/prefill/wmma_gemm.cu)
- `STRATA_PF_FUSED_TILE`  (src/prefill/moe_fused_iq.cu)
- `STRATA_PLE_GGUF`  (src/kernels/ple_parity.cpp)
- `STRATA_PROMPT_ATTN_Q4`  (src/kernels/cuda/qsa_prompt_attn.cu)
- `STRATA_PROMPT_ATTN_V1`  (src/kernels/cuda/qsa_prompt_attn.cu)
- `STRATA_QSA_CLUSTER`  (src/kernels/cuda/qsa_select.cu)
- `STRATA_QSA_WARP`  (src/kernels/cuda/qsa_prompt_attn.cu)
- `STRATA_SELECT_SIMT`  (src/kernels/cuda/qsa_select.cu)
- `STRATA_SESSION_GOLDEN_PRINT`  (src/core/conversation_file_test.cpp)
- `STRATA_SM70_TABLE`  (src/kernels/cuda/fused_gr.cu)
- `STRATA_STARTUP_UNBUFFERED`  (src/core/expert_source.cpp)
- `STRATA_TOPK_ACTIVE_ANY`  (src/kernels/cuda/qsa_select.cu)
- `STRATA_TOPK_CAPACITY_GUARD`  (src/kernels/cuda/qsa_select.cu)
- `STRATA_TOPK_STREAM`  (src/kernels/cuda/qsa_select.cu)
- `STRATA_UMA_HEADROOM_GIB`  (src/core/expert_cache.cpp)
- `STRATA_WDDM_BUDGET`  (src/core/device.cu)
- `STRATA_WMMA_BF16`  (src/prefill/gemm.cu)
- `STRATA_WMMA_GEMM`  (src/prefill/gemm.cu)

## 4 X 实质候选池（132 条，按首命中文件）

- `STRATA_ADAPT_JOB_CPU`  (src/program/generate.cpp)
- `STRATA_ADAPT_LAG`  (src/program/generate.cpp)
- `STRATA_ADAPT_NOWAIT`  (src/program/generate.cpp)
- `STRATA_ARGMAX_MULTI`  (src/kernels/cuda/sampler.cu)
- `STRATA_BATCH_DECODE_SHARE`  (src/program/generate.cpp)
- `STRATA_BATCH_YIELD_CHUNKS`  (src/program/generate.cpp)
- `STRATA_CACHE_MESSAGE_BOUNDARY`  (src/program/generate.cpp)
- `STRATA_CKPT_REREAD`  (src/program/generate.cpp)
- `STRATA_COMMIT_SYNC`  (src/core/verify.cpp)
- `STRATA_DEC_BATCH`  (src/kernels/cuda/shared_expert.cu)
- `STRATA_DENSE_MMQ`  (src/prefill/gemm.cu)
- `STRATA_DF_BRANCH`  (src/core/verify.cpp)
- `STRATA_DF_PLE`  (src/core/verify.cpp)
- `STRATA_DF_QB_Q4`  (src/core/verify.cpp)
- `STRATA_EMULATE_CC`  (include/strata/core/emulate.hpp)
- `STRATA_FORCE_ISA`  (src/kernels/cpu/expert_layout.cpp)
- `STRATA_FS_ADMIT`  (?)
- `STRATA_FS_BUDGET`  (?)
- `STRATA_FS_DEPTH`  (?)
- `STRATA_FS_VERIFY`  (?)
- `STRATA_FUSED_SWIGLU_Q81`  (src/kernels/cuda/shared_expert.cu)
- `STRATA_FUSE_HEAD_GR`  (src/core/mtp.cpp)
- `STRATA_GDN_COMMIT_SPLIT`  (src/kernels/cuda/verify_kernels.cu)
- `STRATA_GDN_CONVL2`  (src/prefill/kernels.cu)
- `STRATA_GDN_CONV_SERIAL`  (src/prefill/kernels.cu)
- `STRATA_GDN_NOY`  (src/prefill/kernels.cu)
- `STRATA_GDN_PP`  (src/prefill/kernels.cu)
- `STRATA_GDN_REC_HEADS`  (src/prefill/kernels.cu)
- `STRATA_GDN_SPLIT`  (src/kernels/cuda/verify_kernels.cu)
- `STRATA_GROUPED_PAIR_MIN_HITS`  (src/kernels/cuda/s2_expert_grouped.cu)
- `STRATA_GROUPED_V1`  (?)
- `STRATA_GROUP_COPY`  (src/prefill/prefill.cpp)
- `STRATA_GR_DOWN_MAX4`  (src/kernels/cuda/fused_gr.cu)
- `STRATA_GR_UNFUSED`  (src/prefill/prefill.cpp)
- `STRATA_GR_V3`  (src/kernels/gr_parity.cpp)
- `STRATA_HC_Q8`  (src/core/native_dense.cpp)
- `STRATA_HC_Q8_INJECT`  (src/core/native_dense.cpp)
- `STRATA_HC_SPLIT`  (src/kernels/cuda/fused_gr.cu)
- `STRATA_HC_UPMIX`  (src/prefill/prefill.cpp)
- `STRATA_HIP_PROMPT_F16`  (src/prefill/gemm.cu)
- `STRATA_HIP_ROUTER_FAST`  (src/kernels/cuda/router_top10.cu)
- `STRATA_HIP_SWIGLU_FUSED`  (?)
- `STRATA_INDEXER_PER_TOKEN`  (src/prefill/prefill.cpp)
- `STRATA_IO_PF_AHEAD`  (src/core/expert_source.cpp)
- `STRATA_IO_PF_STAGE`  (src/core/expert_source.cpp)
- `STRATA_IO_THREADS`  (src/platform/direct_file.cpp)
- `STRATA_IQ_MT_MIN`  (src/kernels/native_expert_parity.cpp)
- `STRATA_IQ_PREFETCH`  (src/kernels/cpu/iq_avx1.cpp)
- `STRATA_IQ_STAGE_GRID`  (src/kernels/cuda/iq_kernels.cu)
- `STRATA_IQ_STAGE_GRID_MMVQ`  (src/kernels/cuda/iq_kernels.cu)
- `STRATA_ISA_FLOOR`  (?)
- `STRATA_KEEP_MAPPING`  (src/program/generate.cpp)
- `STRATA_KV_GROW_FLOOR`  (src/program/generate.cpp)
- `STRATA_KV_GROW_INIT`  (src/program/generate.cpp)
- `STRATA_KV_GROW_STEP`  (src/program/generate.cpp)
- `STRATA_LFUSE_GATE`  (src/core/verify.cpp)
- `STRATA_LFUSE_PAIR`  (src/core/verify.cpp)
- `STRATA_LOGPOS_EXTRA`  (src/program/generate.cpp)
- `STRATA_LOOKAHEAD_K`  (src/program/generate.cpp)
- `STRATA_LOOKUP_CHAIN_FIXED`  (src/program/generate.cpp)
- `STRATA_MMQ_RESIDENT_SORT_NE`  (src/prefill/mmq_resident_sort.hpp)
- `STRATA_MMVF_ROWS`  (src/kernels/cuda/native_bf16.cu)
- `STRATA_MMVQ_WAVE`  (src/kernels/mmvq_multi_parity.cpp)
- `STRATA_MTP_BATCH`  (src/prefill/prefill.cpp)
- `STRATA_MTP_BATCH_F16`  (src/prefill/prefill.cpp)
- `STRATA_MTP_BATCH_RING`  (src/prefill/prefill.cpp)
- `STRATA_MTP_CATCHUP_ALL`  (src/core/mtp.cpp)
- `STRATA_MTP_FULL_HEAD`  (src/core/mtp.cpp)
- `STRATA_MTP_PREFILL_SYNC`  (src/core/mtp.cpp)
- `STRATA_MTP_TOP2`  (src/core/mtp.cpp)
- `STRATA_NORM_ROPE`  (src/kernels/cuda/native_rope.cu)
- `STRATA_NO_BATCH_KV_STEP`  (src/core/mtp.cpp)
- `STRATA_NO_LARGEPAGES`  (src/core/pinned.cu)
- `STRATA_NO_MMVQ_ROWS2`  (src/kernels/cuda/native_mmvq.cu)
- `STRATA_NO_MULTI_GR`  (src/kernels/cuda/fused_gr.cu)
- `STRATA_NO_NORM_ROPE`  (src/kernels/cuda/native_rope.cu)
- `STRATA_OLD_GROUPED`  (src/kernels/cuda/s2_expert_grouped.cu)
- `STRATA_OLD_SAMPLER`  (?)
- `STRATA_PF_FUSED_KQ`  (src/prefill/moe_fused_iq.cu)
- `STRATA_PF_FUSED_NATIVE`  (src/prefill/moe_fused_iq.cu)
- `STRATA_PF_GEMM`  (src/prefill/gemm.cu)
- `STRATA_PF_HCDOWN`  (src/prefill/prefill.cpp)
- `STRATA_PF_OCC`  (src/prefill/moe_fused.cu)
- `STRATA_PF_OCC_W`  (src/prefill/moe_fused_iq.cu)
- `STRATA_PF_PAD`  (src/prefill/gemm.cu)
- `STRATA_PF_STEP_SYNC`  (src/prefill/prefill.cpp)
- `STRATA_PLE_BATCH`  (src/prefill/prefill.cpp)
- `STRATA_PREFILL_BF16X2`  (src/prefill/prefill.cpp)
- `STRATA_PREFILL_CPU_SHARE_MAX`  (src/prefill/prefill.cpp)
- `STRATA_PREFILL_EQUAL`  (src/program/generate.cpp)
- `STRATA_PREFILL_GROUP_GATHER`  (src/prefill/prefill.cpp)
- `STRATA_PREFILL_ISSUER`  (src/prefill/prefill.cpp)
- `STRATA_PREFILL_LEND_PCT`  (src/program/generate.cpp)
- `STRATA_PREFILL_MMQ`  (src/prefill/prefill.cpp)
- `STRATA_PREFILL_RING`  (src/prefill/prefill.cpp)
- `STRATA_PREFILL_STREAM_AHEAD`  (src/prefill/prefill.cpp)
- `STRATA_PREFILL_STREAM_MIN`  (src/prefill/prefill.cpp)
- `STRATA_PROMPT_ATTN_OLD`  (src/prefill/prefill.cpp)
- `STRATA_Q6P_GRID`  (src/kernels/cuda/native_mmvq.cu)
- `STRATA_Q6_PACKED`  (src/kernels/cuda/native_mmvq.cu)
- `STRATA_QSA_EARLY_EXIT`  (src/kernels/cuda/qsa_select.cu)
- `STRATA_READ_AHEAD`  (src/platform/memory.cpp)
- `STRATA_REFILL_BLOCKING`  (src/program/generate.cpp)
- `STRATA_REFILL_SERIAL`  (src/program/generate.cpp)
- `STRATA_RESIDENT_HEADROOM_GIB`  (src/program/generate.cpp)
- `STRATA_RING_BYTES`  (src/prefill/prefill.cpp)
- `STRATA_ROPE_TABLE`  (src/kernels/cuda/native_rope.cu)
- `STRATA_ROUTER_BLOCK`  (src/kernels/cuda/router_top10.cu)
- `STRATA_ROUTE_PER_TOKEN`  (src/core/layer.cpp)
- `STRATA_ROUTE_PROJ_PER_TOKEN`  (src/core/layer.cpp)
- `STRATA_ROUTE_RESIDENT_RANKS`  (src/core/verify.cpp)
- `STRATA_S2_SWIGLU_Q8`  (src/kernels/cuda/s2_expert_grouped.cu)
- `STRATA_SAMPLER_ONE_BLOCK`  (?)
- `STRATA_SCORES_MULTI`  (src/kernels/cuda/qsa_select.cu)
- `STRATA_SELECT_OLD`  (src/prefill/prefill.cpp)
- `STRATA_SELECT_WMMA`  (src/kernels/cuda/qsa_select.cu)
- `STRATA_SEL_OVERLAP`  (src/prefill/prefill.cpp)
- `STRATA_SESSION_BUFFERED`  (src/core/conversation_file.cpp)
- `STRATA_SPEC_DEPTH`  (src/program/generate.cpp)
- `STRATA_SPEC_MIN_TEMP`  (include/strata/core/spec_prob.hpp)
- `STRATA_SPEC_PROB`  (include/strata/core/coupled_draft.hpp)
- `STRATA_SPEC_PROB_DT`  (include/strata/core/spec_prob.hpp)
- `STRATA_SPEC_PROB_GATE`  (include/strata/core/spec_prob.hpp)
- `STRATA_STAGE_PIN`  (src/core/expert_source.cpp)
- `STRATA_STAGE_TRIM`  (src/program/generate.cpp)
- `STRATA_TG_FLUSH_US`  (src/core/session.cpp)
- `STRATA_TOPK_OLD`  (src/kernels/cuda/qsa_select.cu)
- `STRATA_UNBUFFERED_LOAD`  (src/core/expert_source.cpp)
- `STRATA_VERIFY_DEBUG`  (src/core/verify.cpp)
- `STRATA_VERIFY_NODES`  (src/core/verify.cpp)
- `STRATA_VERIFY_QDEDUP`  (src/core/verify.cpp)

## 5 M 面（73 条，单卡不触发）

`STRATA_ARENA_LOCK` `STRATA_ARENA_MMAP` `STRATA_ARENA_PIN_GIB` `STRATA_ARENA_RELEASE` `STRATA_AUX_CPUS` `STRATA_AUX_STAGER` `STRATA_DISJOINT_ADAPT` `STRATA_DMA_BATCH` `STRATA_EARLY_REMOTE_CONTEXTS` `STRATA_EXCHANGE_ROTATE` `STRATA_GDN_PIPELINE` `STRATA_KV_MAIN_OFF` `STRATA_KV_PREFETCH` `STRATA_KV_RING_OFF` `STRATA_KV_ROT` `STRATA_KV_STAGE_OWN` `STRATA_LAYER_SPLIT_GATE` `STRATA_LAYER_SPLIT_PROBE` `STRATA_NO_ARENA_THP` `STRATA_OWNED_PRICE` `STRATA_PARTIAL_PIN` `STRATA_PARTIAL_PIN_GIB` `STRATA_PEER_DIRECT` `STRATA_PEER_HOT` `STRATA_PEER_HOT_AT` `STRATA_PEER_NO_P2P` `STRATA_PF_PEER_COMPACT` `STRATA_PF_PEER_F16` `STRATA_PF_PEER_GATHER` `STRATA_PF_PEER_HOST` `STRATA_PF_PEER_OUT_PIPE` `STRATA_PF_PEER_RING` `STRATA_PF_PEER_STREAM` `STRATA_PF_PEER_SUMS` `STRATA_PF_PEER_XSTREAM` `STRATA_PIN_GUARD` `STRATA_PIN_RESERVE_GIB` `STRATA_PIPELINE_ADAPT_ASYNC` `STRATA_PIPELINE_AGREE` `STRATA_PIPELINE_DEBUG` `STRATA_PIPELINE_DOOM_SKIP` `STRATA_PIPELINE_FORCE_MISS` `STRATA_PIPELINE_LOG` `STRATA_PIPELINE_LOOKUP_PON` `STRATA_PIPELINE_PRESTAGE` `STRATA_PIPELINE_SNAP_OVERLAP` `STRATA_PIPELINE_SPEC_DEPTH` `STRATA_PIPELINE_THETA` `STRATA_PIPELINE_TRACE` `STRATA_REMOTE_SPIN` `STRATA_REMOTE_ZEROCOPY` `STRATA_RESIDENT_PIN` `STRATA_SH_FORK_LATE` `STRATA_SNAPSHOT_FULL_CAPTURE` `STRATA_SNAPSHOT_VERIFY` `STRATA_SPLIT_COVER_B` `STRATA_SPLIT_MISS_MS` `STRATA_SPLIT_NEAR_TIE_PCT` `STRATA_SPLIT_OWN` `STRATA_SPLIT_OWN_BUFFERS` `STRATA_SPLIT_OWN_PLACE` `STRATA_SPLIT_SMALL_MAX` `STRATA_SPLIT_SMALL_OWN` `STRATA_SPLIT_TIMING` `STRATA_SSD_KEEPALIVE` `STRATA_SSD_KEEPALIVE_WINDOW` `STRATA_STAGER_BATCH` `STRATA_STAGER_RING` `STRATA_STAGER_SLEEP` `STRATA_STAGER_THREADS` `STRATA_VERIFY_ALL_RESIDENT` `STRATA_VERIFY_COMPLEMENT` `STRATA_VERIFY_DEVICE_PLAN`

## 6 已知运行期门（"编进去"!= "拨得动"）

- `STRATA_PROMPT_ATTN_Q4` / `..._V1`：需 `pools.k_q4 != nullptr`（即 `--kv q4_0`）==> 我方 `k8v4` 不可达（同 `P55`/`P56` 形态）
- `STRATA_PLE_*`：需 `--ple-gguf` / `--ple-io`（我方 args 都没有 ==> 不可达，W774 已证）
- `STRATA_PEER_*` / `--peer-device`：需第二块卡
- `arch_defaults.cpp` 表内项（如 `GDN_PP` / `Q6_PACKED`）：**只在 gfx12/gfx1151 自动开**，gfx906 恒空表 ==> 须显式设 env；表内收益数字**全是 gfx1151/Aurora 的**
- 改答案类（须配 `P51` 的 `STRATA_LOGPOS` 门）：`SPEC_PROB*` / `OLD_SAMPLER` / `HC_Q8` / `PF_GEMM` 等

## 7 优先族（我们有独立线索的）

- **GDN 族**：`GDN_PP` / `GDN_CONVL2` / `GDN_NOY` / `GDN_COMMIT_SPLIT` / `GDN_REC_HEADS` / `GDN_CONV_SERIAL`（`P41 §4` 已筛出）
- **Q6/Q8 pack 族**：`Q6_PACKED` / `Q8_PACKED`（`P45` 实读 Q8_0 张量 303；车在跑）
- **verify/commit 族**：`VERIFY_QDEDUP` / `COMMIT_SYNC` / `DF_BRANCH` / `LFUSE_PAIR`
- **prefill 族**：`PF_GEMM` / `PF_PAD` / `PREFILL_STREAM_AHEAD` / `PREFILL_BF16X2` / `SELECT_OLD`
- **MTP 族**：`MTP_FULL_HEAD` / `MTP_CATCHUP_ALL` / `MTP_PREFILL_SYNC` / `FUSE_HEAD_GR`
- **采样族**：`OLD_SAMPLER` / `SAMPLER_ONE_BLOCK` / `ARGMAX_MULTI`
- **KV/IO 族**：`KV_GROW_INIT/STEP/FLOOR` / `IO_THREADS` / `READ_AHEAD` / `IO_PF_AHEAD`
- **会话族**：`SESSION_BUFFERED` / `CACHE_MESSAGE_BOUNDARY`

## 8 局限

1. **名字筛是上界，不是定论**：M/D/C/X 四桶按名字+首命中文件划分，抽样 12 条细读守卫后**有 4 条落在预期之外**（`ATTN_PRE75` 经宏间接排除、`PF_BK64` 是 gfx11、`PROMPT_ATTN_Q4` 需 q4_0、`TOPK_STREAM` 在 `!__HIPCC__` 里）。==> 132 里仍会掉一部分，**逐条守卫判定 = W17 的正式动作**。
2. **"编进去" != "有收益"**：多数是上游未文档化的内部旋钮（无 release note、无社区数据）；有明确收益线索的只有 §7 里那几族。
3. 本清点是**名字面**，未覆盖同一 env 的多分支语义（如 `=0` vs `=1` vs 设值）。

## 9 产物

- `_w17_scan.txt`  (68439 B / `60717548ddb6902c581184fb5d847313`)
- `_w17_stack.txt`  (27775 B / `db989437f760a02ff8b261e76743ce6e`)
- `_w17_verdict.tsv`  (20233 B / `a60b67b4862046ffeaecd525779ff47e`)

> 扫描脚本：`deploy/tmp/_w17_scan.py` / `_w17_stack.py` / **`_w17_gen.py`（canonical，生成本件）**；`_w17_final.py` 为**被取代**的旧版（DIAG 多 `_GATE$`，给 X=129）（本地 Python + ssh base64 通道；容器 `--rm`，无 GPU、未停生产）。


> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `8f4153e78369dc421a96cd834fbcfa59`（字节 16839）。
