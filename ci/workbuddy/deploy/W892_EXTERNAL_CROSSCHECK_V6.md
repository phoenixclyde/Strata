# W892 · 外部证据交叉核对 V6.2：分享对话 26 条主张逐条对账；`v_dot8` 在 7 个 fork 里均不存在

**来源**：用户给出的 WorkBuddy 分享会话（30 条消息），本地历史账本、166 当前源码，以及 17 个外部仓库的实际源码
（iacopPBK / fuutott / mx-llama / llama.cpp / Castagna / expert-pool / hipfire / Strata 上游与 NVFP4 / NInfer 两支 /
wiki-gfx906 / DeepInfer / deepseek-recipe / vLLM / SGLang / TensorRT-LLM）。所有仓库提交号见 §8.1。

**最终结论**：

1. **`STRATA_EXPERT_V2K` 不是新候选**。W824 已测三次并定案不采纳；当前 `iq_kernels.cu` 相对当时 `v0.2.7.1` **0 commit、0 diff**，不得重复消耗停机窗口。
2. **分享会话把 hipfire 读反了**。原文最终按内核区分「ILP/指令发射受限」与「内存停顿」，并未给出统一“换 `v_dot8` 后 decode 1.5–2.5×”的实测；`v_dot8_i32_i4` 在其文中只是未测的后续建议。
3. **V6.1 当时新增 R49**；V6.2 再按源码产出 **R50（router BF16 GEMV）** 和 **R51（gfx906 MMQ 向量化/流水线，prefill-only）**。
4. **R48 锁频已证否**：decode 时 sclk 始终 1725 MHz，功率 114–220 W，未撞 300 W 墙。
5. **“iacopPBK 有 tiled + v_dot8”这句话是假的**：`iacop/fuutott/mx-llama/llama.cpp/Castagna/expert-pool` 的源码里
   `__builtin_amdgcn_sdot8` / `v_dot8_i32_i4` 实现数都是 **0**；只有 hipfire 的文档把它列为“speculative/未实现”。
   iacop 真正的改动是 **tiled MMQ 的 128-bit 向量 load、Q8 软件流水、Y-tile prefetch、warp-coop MMVQ、Q8 attention**。
6. **Strata 不是“没有 gfx906 内核”**：上游 `docs/AMD_HIP.md` 的 gfx906 节自己列了 8 类专用实现；本 fork 另有
   `native_mmvq / fused_gr / iq_kernels / qsa_* / native_router / bf16_gemv` 共 **18,693 行**。 llama.cpp 只承担
   **prefill 的 K-quant MMQ**（`strata_kq` 动态库），不是“全部矩阵乘”。

---

## 1 分享会话逐项对账

| 分享会话的主张 | 历史 / 源码 / 外部原文裁定 |
|---|---|
| `STRATA_EXPERT_V2K` 是值得新试的 s27 多行专家内核 | **重复开项**。W824 §3：N0 41.8 → T1 45.0 的 +7.7% 被 N0b/T1b **46.9/46.9** 配对推翻；§9.1 第三次 V1 45.1 对基线 45.9/44.5，仍无差异。P153 已是 REJECTED |
| 换 `v_dot8_i32_i4`，decode 45→70–110 | **没有这笔实测**。LLVM 签名是 `src0i4x8, src1i4x8`，即 **i4×i4**，不是分享会话说的 int4×int8；hipfire 也只把它列为后续建议 |
| “VALUBusy 卡死约 48%，所以统一是 ALU 发射墙” | **原文不支持**。hipfire 实测 VALUBusy 26–41%；后续又按 kernel 细分：residual 的 prefetch 有 +4.8%，其余三个 kernel 的 prefetch 为 flat/noise |
| “带宽十几%，所以统一不是带宽问题” | **同样过度概括**。hipfire 的总体是 HBM-bound but not saturated；不同 GEMV 的限制因素不同。我们的 R37/R38 也只能约束本机对应内核，不能外推成整个 decode 的统一定律 |
| 锁频通常 +5–15%，UPP 再 +10–20% | **本机锁频前提不存在**：decode 时 sclk 已是最高档 1725 MHz；功率波动不是 DVFS，且未撞 cap。UPP 不进入当前软件调优队列 |
| ring 加深、32 IO 线程、pinned staging | R15 已测 ring 三档完全相同；`wait copy` 等的是专家 blob 拷贝事件，不是 unpinned host copy；IO prefetch 历史实测 0 read ahead |
| `resident-cpu-experts`、mmap、专家分层是当前大头 | 当前专家命中约 98.9%、PCIe 约 0，驻留/换入不是当前窗口瓶颈；不为分享会话重开 |
| `--kv int8 --kv-resident 32768` | 生产已是更细的 `k8v4`，max-context 262144；KV 读占比低且现役权重已补 32K/128K needle，不换回较粗档位 |
| `--spec 4 --spec-min-p 0.5` 可再带来 20–40% | 生产已是 `--spec 4`；0.50 历史 −14.5%，0.40 最新四臂打平，spec 阶梯 R43 已结，不能套别人的收益率 |
| hipBLASLt 调优表 | 本机已走到 codegen/加载层，但 rocBLASLt 无可用 gfx906 解；X17 已关闭 |
| Strata 没有 gfx906 专用内核，全部只是 llama.cpp MMQ | 对我们的 fork 不成立：`native_mmvq`、`qsa_prompt_attn`、s26/s27、gfx906 arch defaults 都在；llama.cpp 血统不等于没有专用路径 |
| NInfer 可直接给 MI50 提供新引擎路线 | 官方路线是 NVIDIA CUDA + 特定 sm 架构与专用制品，不是 gfx906 可直接构建的引擎；只借鉴其按模型/内核特化的方法，不进部署队列 |

## 2 hipfire 原文的精确含义

原始资料：`nwoolmer/hipfire/docs/perf-checkpoints/2026-05-05-gfx906-decode-investigation.md`，MI50 / Qwen3.5 9B / batch=1 / 128-token AR decode。

- 初始：hipfire 50.7 tok/s，stock llama.cpp 61.55，skyne98 63.48；总体仍是 **HBM-bound but not saturated**。
- PMC：四类 GEMV 的 VALUBusy **25.9–41.4%**，MemUnitStalled **0.95–4.23**。
- residual 软件流水：51.9→54.4 tok/s（**+4.8%**）；FetchSize 基本不变，说明收益来自 ILP，不是少读字节。
- 其余 gate/up、qkv、qkvza 的 prefetch 无效；后续 dp4a/Q8_1 路径才带来进一步提升。
- 全阶段约 50.7→63.0 tok/s 是**多项改动累计**，不能归因给 dot8，更不能直接套到我们 125B MoE 的端到端。

iacopPBK 的官方源码确有 `gfx906_prefetch_y_tile_v4`：提前一轮用 `global_load_dword` 预热 Y tile，再显式 consume；这证明机制存在，但不证明它在我们的 `native_mmvq` 形状上有效。

## 3 R47 为什么关闭而不是再测一次

| 证据 | 结果 |
|---|---|
| W824 首轮 | T1 45.0 对 N0 41.8，看似 +7.7% |
| 配对复跑 | N0b 46.9 / T1b 46.9，**0.0%**；首轮是容器漂移 |
| 第三次 | V1 45.1 对基线 45.9/44.5，仍无差异；W824 §9.1 写“定案不采纳” |
| 当前源码同一性 | 166 `pr/strata-fork@d963c791`：`git rev-list --count v0.2.7.1..HEAD -- src/kernels/cuda/iq_kernels.cu` = **0**，`git diff --quiet` = **0** |
| 账本 | P153 = **REJECTED**；R47 在 W892 初版被误开，现改回 DONE_NEG |

⇒ **不再重启、不改 env**。若未来 s27 源码发生实质变化，必须作为“新源码版本”重新登记，而不是拿今天的二进制重复旧实验。

## 4 R48 锁频：已结

decode 期间每 0.6 s 采样：sclk 全程 **1725 MHz（level 8，最高档）**，功率 **114–220 W**，请求结束才降至 925 MHz / 17 W。功率变化是同一时钟下工作量变化，不是频率抖动；未撞 300 W cap。⇒ DONE_NEG。

## 5 R49：唯一新增，dense GEMV 软件流水 / ILP 探针

**为什么不与旧项重复**：

- R23 改的是每波行数 R；R43 测的是专家 GEMV 与 spec；R49 针对 **dense `native_mmvq` 的下一轮 load 与当前计算重叠**。
- 当前 `native_mmvq.cu` 未见 `prefetch/global_load/readfirstlane` 实现；而 QSA 瘦矩阵、head 等 dense 相位仍低于可达屋顶，存在可判空间。
- 外部只提供“同架构、不同内核曾有效”的先验，不提供收益承诺。

**四道门**：

1. **静态门**：确认目标 kernel 的汇编中 load→dot 依赖链确有空窗；若已有足够独立 load/ILP，直接关闭。
2. **探针门**：只改独立 `native_mmvq` 微基准，逐形状比较原版图与软件流水图；主判据时间，门槛 `|Δ| ≥ 2×CV`，逐位相同。
3. **停机条件**：任一代表形状收益 <2×CV、VGPR 增长导致 occupancy 下降、或 prefetch 变成额外流量 ⇒ 不开服务 A/B。
4. **服务门（需另批）**：只有探针过门才编译候选引擎；生产配置与当前引擎在探针阶段完全不动。

**成本**：第一阶段只读源码/汇编 + 独立容器探针，零停服；不预登记“预期提升百分比”。

## 6 新规矩：新候选先查历史，再查外部

1. 新 R 项先搜 `PARAM_REGISTER.tsv` 与 `PROGRESS.tsv` 的同名 env、同一 kernel、同一机制；已有 REJECTED/DONE_NEG 时，只有**新源码或新实测矛盾**才能重开。
2. 外部“指令更快”必须依次回答：操作数语义是否匹配、目标单元是否真是瓶颈、原项目是否端到端实测、我们的 kernel 是否同形。
3. 任何倍数都要带分子分母和负载；kernel、相位、整窗口、端到端不得互换。

## 7 原始来源

- hipfire decode 调查：<https://github.com/nwoolmer/hipfire/blob/master/docs/perf-checkpoints/2026-05-05-gfx906-decode-investigation.md>
- iacopPBK gfx906 fork：<https://github.com/iacopPBK/llama.cpp-gfx906>
- iacopPBK Y-tile prefetch 源码：<https://raw.githubusercontent.com/iacopPBK/llama.cpp-gfx906/master/ggml/src/ggml-cuda/gfx906/matmul/mmq-prefetch.cuh>
- LLVM gfx906 指令签名（搜索快照与汇编文档）：`v_dot8_i32_i4 vdst, src0i4x8, src1i4x8, src2i32 clamp`
- 本地历史：W824 §3/§9.1、W825 §5、P153、W789（TILEV 降低 MLP 的反例）、W863/R23、W879/R43。

---

## 8 分享会话全条目对账（2026-11-02 21:xx，源码级）

### 8.1 已拉源码清单（`albus/w895/forks/`）

| 仓库 | 提交 | 用途 |
|---|---|---|
| `iacopPBK/llama.cpp-gfx906` | `125db33`（2026-08-23，README 已标“not updated”） | 原 gfx906 fork，MMQ/MMVQ/FATTN |
| `fuutott/llama.cpp-gfx906` | `c84c609`（2025-11-24） | iacop 前身/同族 |
| `mxxm-t/mx-llama.cpp` | `c4d12e2`（2026-10-15） | iacop README 指向的活跃 fork，gfx906 MMQ config + q8_repack |
| `ggml-org/llama.cpp` | `cd8427d`（2026-11-02） | 上游基准 |
| `benpeterson40/castagna-veloce` | `3483d46`（2026-10-06） | 同模型 gfx906 引擎，QSA/KQ/Q8/HC/MoE |
| `atretador/gfx906-16gb-expert-pool` | `6ff15f1`（2026-10-05） | 16GB gfx906 专家池 |
| `nwoolmer/hipfire` | `5716dcf`（2026-05-10） | MI50 实测/PMC/MQ4 |
| `Niko1221/Strata` | `c62d5e3`（2026-10-31） | 上游 Strata |
| `sergqwer/strata-nvfp4` | `586dc5e`（2026-10-24） | RDNA/NVFP4 Strata fork |
| `Neroued/ninfer` | `a754fcf`（2026-11-02） | NInfer 上游 |
| `T-Crypt/ninfer-4090` | `3011260`（2026-10-03） | NInfer sm89 分支 |
| `skyne98/wiki-gfx906` | `c08628c`（2026-02-21） | gfx906 文档，不是内核仓库 |
| `deepseek-ai/DeepInfer` | `5537415`（2026-10-25） | DeepSeek 专用引擎 |
| `deepseek-ai/deepseek-recipe` | `935817c`（2026-10-20） | API 协议转换，无 GPU kernel |
| `vllm-project/vllm` | `30565c3`（2026-11-02） | 通用服务引擎 |
| `sgl-project/sglang` | `755783e`（2026-11-02） | 通用服务引擎 |
| `NVIDIA/TensorRT-LLM` | `8d4901e`（2026-11-02） | NVIDIA 专用 |

**点名但 404**：`skyne98/llama.cpp-gfx906`、`NicholasJunjie/Strata-rdna3`。前者只剩 wiki（无内核）；
后者以 `sergqwer/strata-nvfp4` 的 RDNA3 文档/源码替代核查。

### 8.2 逐条判定（“有吗/在用吗/优化” × “别人有吗/谁好/能移植”）

| # | 分享会话条目 | 我们：有吗 / 生产在用 / 可优化 | 外部源码判定与移植性 |
|---:|---|---|---|
| 1 | 4 容器 + 路由做 4 人并发 | 部署层已有单容器单序列；无代码改动 | 与内核无关；我们的真实约束是单卡，不是并发调度 |
| 2 | vLLM 跑不了 2-bit Strata GGUF | **正确**：量化和 pack 是 Strata/llama.cpp 契约 | vLLM CMake 虽列 gfx906，但平台逻辑只优化 gfx90a/942/950；无 MI50 调优路径，不换引擎 |
| 3 | DeepInfer / deepseek-recipe | 不用 | DeepInfer 仅 SM100 + Ascend 950；recipe 是纯协议库、无 kernel。均不可移植到 gfx906 |
| 4 | NInfer 4090 / MTP3 / KV 池 / ReplaySSM | Strata 已有 MTP、会话 KV、前缀复用 | 上游 NInfer 只接受 `sm_120a/121a`，4090 分支只接受 `sm_89`；无 AMD 编译路径 |
| 5 | Strata 没有自己的 gfx906 内核 | **假**。上游 gfx906 节列 8 类专用实现；本 fork 另有 18,693 行自有 kernel | 不需要移植“从无到有”；需要的是逐项比较 |
| 6 | 量化矩阵乘全部借 llama.cpp MMQ | **假**。只有 prefill 的 K-quant MMQ 用 `strata_kq`；dense prefill 走 rocBLAS，decode 走自有 GEMV/专家/QSA | 不存在“整套替换 MMQ”的入口 |
| 7 | Strata 的 MMQ 是旧“行并行”变体 | **半假**。它是 llama.cpp **0.4.1 的 tiled MMQ**（`MMQ_TILE_NE_K/mmq_y`），不是 row-parallel GEMV；但确实缺 iacop 的 gfx906 向量 load/prefetch | iacop/mx 有这些 gfx906 增强；**可移植，但只影响 prefill** |
| 8 | iacopPBK 有 tiled + `v_dot8` | **假**。7 个 fork（iacop/fuutott/mx/upstream/Castagna/expert-pool）`sdot8/v_dot8` 实现数 **0**；iacop 只有 `sdot4` | 无可移植 dot8；hipfire 文档也把 dot8 标为 speculative/未实现 |
| 9 | `v_dot8` 把 int4 权重指令减半，decode 45→70–110 | **不可用**。LLVM 签名是 `src0i4x8, src1i4x8`，是 **i4×i4**；我们是 Q4_K 权重 × Q8_1 激活 | 要用必须把激活也压到 4-bit（W4A4），换数值契约，且 ALU 不是墙 |
| 10 | dp4a 发射率 48% 是硬件墙 | **不成立**。hipfire PMC 是 VALUBusy 26–41%；我们 R38/R37 也不是 ALU 墙 | 没有可移植的“解发射率墙”代码 |
| 11 | tiled MMQ + LDS + 异步复用 | 我们的 MMQ 已 tiled/LDS；缺 gfx906 专用 128-bit load、Y-tile prefetch、Q8 流水 | iacop/mx 有；可做 **R51**，只以 prefill 判据验收 |
| 12 | warp-coop MMVQ（2 rows/wave、无 LDS） | `native_mmvq` 已有自研 R 表/多行；R23 上生产 +4%，469 GB/s | iacop 的 MMVQ 是 llama.cpp 形状；没有证据比我们 469 GB/s 更好，先不移植 |
| 13 | Q8 flash attention | 自有 `qsa_prompt_attn` 是 FP32，R46 只到 FP32 峰 11–16% | **Castagna 有同模型 gfx906 QSA**：48 行/块、64-cell、`v_dot2_f32_f16`、不建 mask；2304 cells T=128 603 vs 772 µs。**R46 应参考/移植** |
| 14 | 小批量 K-quant matvec | 专家读 411 GB/s、命中 98.9%，s27 有 4 rows/warp；没有明显缺口 | Castagna `gcn-kq-matvec` 读 4–8B/lane、LDS 激活，设计相近；无优于 411 的证据 |
| 15 | 路由 + top-k 融合 | 现为 GEMV→top10→plan→doorbell，R50 测 2.09 ms GEMV / 3.895 ms 总 | Castagna `router1_topk_bf16` 把 matvec+top-k 融成一个；可并入 R50 的第二方案 |
| 16 | MoE gate/up + SwiGLU / 融合 | 自有 grouped expert + MMQ + fused_gr；HC 已融合 | Castagna 的 i-quant MoE 收益大，但我们是 Q4_K + 自有布局；不能整段照搬 |
| 17 | HC 持久化/融合 | 自有 `fused_gr`；R38 实测净负 +2.8% | Castagna 的 HC 融合带 TP all-reduce；单卡不适用，单卡 HC 已到边界 |
| 18 | MTP 图复用 / catch-up / draft-vocab | MTP 已在生产；`--mtp-draft-vocab` 未设（P47/X4） | Castagna 实现 `LLAMA_MTP_DRAFT_VOCAB` 前缀；**X4 获得第二个外证**，仍需代表语料 |
| 19 | `--spec` / `--spec-min-p` 再抬窗口 | 生产 `--spec 4` / 0.70；R43 九臂无效，0.50 历史 −14.5% | 无可移植新证据；不重开 |
| 20 | KV int8 / kv-resident / 262144 | 生产 `k8v4`；W888 现役权重 needle 32k 3/3、128k 1/1 | 上游 16GB 示例是 `--kv int8 --kv-resident 32768`；我们是更细的 k8v4，不回退 |
| 21 | 专家池 / mmap / resident | 7463 槽、21.79 GiB、命中 98.9%、PCIe≈0 | expert-pool 是 16GB 卡的准入修复；我们 32GB + 自有缓存已覆盖，不移植 |
| 22 | hipBLASLt 调优表 | 已判 X17：无 gfx906 可用 solution | RDNA3 fork 的 hipBLASLt 只对 gfx1100/1201；gfx906 不适用 |
| 23 | RDNA3 wave32 + integer dot 移植 | gfx906 是 wave64；我们的 compat 已把 CUDA warp 映射到半 wave | RDNA3 的 wave32 shuffle/packed-byte 不能直接搬；hipBLASLt 也无解 |
| 24 | UPP / 抬 power cap / 锁频 | R48：sclk 1725 MHz、114–220 W、未撞 300 W；无 DVFS 可锁 | 硬件超频不属于源码优化；有风险，不进调优队列 |
| 25 | ROCm 7.14 是 gfx906 的唯一现实栈 | 生产已 ROCm 10.1 / HIP 7.16（TheRock），可运行 | 7.14 是上游 Strata 文档的社区镜像基线，不是必须降级；不换 |
| 26 | 1.5–2.5× / 45→70–110 | 我们的实测 decode 真实流量 41.6–51.1 tok/s，短上下文 75.8；没有 MMQ 因果链 | 外部没有任何 fork 给出该倍数的源码或端到端证据；不立收益承诺 |

### 8.3 真正值得做的三项

| 项 | 做什么 | 判据 |
|---|---|---|
| **R51（新）** | 把 iacop/mx 的 gfx906 **MMQ 128-bit load / Q8 software pipeline / Y-tile prefetch** 合进 Strata 的 `ggml-tq-overlay/mmq.cuh`，只走 prefill 的 K-quant MMQ | 同 prompt prefill timing ≥2×CV、数值逐位/argmax 门；**不得拿 decode tok/s 验收** |
| **R46（补外证）** | 对照 Castagna `fattn-qsa-gcn` 的三 kernel QSA：不建 mask、48 行/块、f16 QK、64-cell 分段 | 长 prompt QSA attn 从 18.9% 降；独立 bench 先过，不动生产 |
| **R50（补方案）** | router GEMV 2.09 ms/60 GB/s；第二方案参考 Castagna `router1_topk_bf16` 的 matvec+top-k 融合 | top-k ids 逐位；服务侧仍 2×CV |

### 8.4 结论

分享会话的**方向有一半是对的**：gfx906 的 MMQ/注意力确实还有可移植的工程优化；但**因果归因是错的**：
不是“Strata 没有内核 / 全部借旧 MMQ”，而是“**Strata 自有 decode 内核 + llama.cpp 的 tiled K-quant MMQ**，
缺的是 gfx906 专用的 load/流水线（prefill）和同模型 QSA（attention）”。而 `v_dot8` 在真实 fork 中不存在，
也不是 Q4_K×Q8_1 可用的指令。**35–45 tok/s 的 decode 瓶颈不在 MMQ，不能靠移植 iacop 的 MMQ 变成 70–110。**
