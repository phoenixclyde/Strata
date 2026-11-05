# R86 完整生产移植 · 状态（唯一权威）

> 立档 W1002；W1003 依据「类型 × 形状 × tile 宽度」实测**重划边界**。
> 本文件是「完整移植」第一问的机器可读答案，由 `ci/round_gate.py --ci` 与
> `ci/repack_ab/verify.py` 强制检查。**没有实测数据不得写 DONE**。

## 0 W1003 改变了什么（先读这一节）

W1001 的公平 A/B 只在 **Q5_1 + 一个形状** 上选了**分派规则挑中的那一个臂**，于是
「320 行慢 15%」被当成了 kernel 的性质。补测三臂（canonical / repacked-32 宽 /
repacked-64 宽）× 生产真实类型与形状后，结论被两件事改写：

1. **那是分派规则，不是 kernel。** 320 行时 w32 = 0.955、w64 = 1.183，
   而 mx 的规则（`use_w32 = n_assign < 2*BN_ID*ne02`，16 专家阈值 4096）恰好
   在这里翻到 64 宽。⇒ **不需要「按段混合分派」，只需要一直用 w32。**
2. **K-quant 的 repack 是净亏损，而生产 gate/up 全是 K-quant。**
   `native_experts.txt` 的列是 `layer gu_type d_type …`：
   gate/up = **Q4_K(12) / Q5_K(13)** @ `[out=1280, K=2560]`；
   down = **Q5_1(7) / Q8_0(8)** @ `[out=2560, K=640]`。
   而 K=640 不是 QK_K=256 的整数倍，**K-quant 在 down 上几何不合法** ——
   Unsloth 的 UD 混合只在 gate/up 上用 K-quant，正是这个原因。

三臂扫描（`WIDTH_SWEEP.tsv`，20 行，ratio = repacked/canonical）：

| 张量 | 类型 | w32 | w64 | 判 |
|---|---|---|---|---|
| gate/up | Q4_K | 2.26–2.98 | 1.02–3.87 | **永不 repack** |
| gate/up | Q5_K | 1.57–2.51 | 1.00–2.25 | **永不 repack** |
| down | Q5_1 | **0.79–0.81** | 0.93–2.28 | **repack，w32** |
| down | Q8_0 | 0.54–0.69 | **0.58–0.61** | **repack**；≤320 行 w32，≥512 行 w64 |

## 1 通道状态

| 通道 | 内容 | 状态 | 证据 / 缺口 |
|---|---|---|---|
| C1 权重上传 | **按角色分层的 repack**：只把 down 在 arena 装载时转成 repacked 布局，gu 保持 canonical 原样 | IN_PROGRESS（设计定稿，代码未动） | 尺寸：Q5_1 dn **中性**（1 228 800 = 1 228 800 B）；Q8_0 dn **+2.3%**（1 740 800 → 1 781 760 B）⇒ `d_stride`/零尾只在 Q8_0 层变 |
| C2 调度分派 | `Context::run` 加 `Product.layout`，down 走 `mmq_gemm_repacked_w32`（Q8_0 大行数走 64 宽）；`expert_stride` 由 `expert_bytes/type_bytes` 换成 `repack_gcn_nbytes` | NOT_STARTED | 生产 `src/prefill/moe_mmq.cu:498` 未改；bench 内分派≠调度 |
| C3 激活对齐 | `mmq::quantize` 的输出与 `block_q8_1_mmq_h` 逐字节断言 | PARTIAL | W1001 起两臂已共用同一份激活；缺 3 条 `static_assert` 的等价测试 |
| C4 融合 | `{MM_ID, MM_ID, GLU}` 的门/上投影 + GLU | **N/A（理由更正）** | 不是「prefill 无红利」，而是**我们已经是单次调用**：`prefill.cpp:5300` `gu.w_rows = 1280` 一次算完 gate+up。上游 #29948(稠密)/#31188(MoE，2026-10-30 合并) 的收益来自省掉第二次 launch，此处不存在 |
| C5 验收 | 逐位等价 + 六长度档 A/B + 2×CV + KL/top-1 + env 开关 + 镜像回滚 | NOT_STARTED | 无 |
| C6 R97 混合分派 | 按 `expert_bounds` 分段分派 | **解散（NOT_APPLICABLE）** | W1003：320 行是分派规则的锅；w32 在 down 全行数档 0.79–0.81，混合分派没有可分的两段 |

**当前结论**：`PRODUCTION_PORT = NOT_DONE`，`src/` `include/` `CMakeLists.txt` 零改动。
生产二进制 md5 仍为 `eea5ea3749ad54b124330386605a18bc`。

## 2 为什么「完整移植」被降级为「down 一路」

W853 P104 的相位剖面：专家 GEMM 29–35%，其中 **down 13% / GU 19–22%**。

- down 13% × (1−0.80) = **−2.6%**（Q5_1 层）；Q8_0 层 −40%，但它只占少数层。
- gu 19–22% 若 repack 会 **变慢 0.2–1.9 倍**，必须排除。
- 合计端到端 ≈ **−2.6% ~ −3.3%**，低于预先定死的 **prefill@2K ≥5%** 判据。

⇒ **全量移植（专家全 repack）是 NO-GO**，不是因为难，而是因为测量说它更慢。
**定向移植（只 down）** 的收益真实但不足以单独开一轮工程；是否做，取决于它与队列里
更大的两块（`dequant` 8–18% / `wait copy` 7–15%）的性价比排序。

## 3 移植前置判据（沿用「测完有实际数据才能做判断」）

- 定向移植（down）准入：`dequant`/`wait copy` 两条先做完或判否，且 down 的 e2e
  实测 ≥2.5%（六长度档、2×CV）。
- 全量移植（gu 也 repack）：**已否**，证据见 §0 表与 `WIDTH_SWEEP.tsv`。
- 任何情况下：`PRODUCTION_PORT` 只有在 C1–C5 全部 DONE 且镜像回滚演练通过后才改写。
