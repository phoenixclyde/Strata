import io, shutil

P = "albus/gfx906_survey/PORT_PLAN.md"
shutil.copyfile(P, P + ".bak_w1037")
s = io.open(P, encoding="utf-8").read()
assert "F 组：手法" not in s

F = """
### F 组：手法（**能拿的不是文件，是这四条**；每条都给了判据 / 样本 / 停机 / 成本）

> 2026-11-07 07:0x 补（机主：「你怎么拿手法。能拿你拿呀。入权威调优或者移植方案啊。」）。
> 本组与 A–D 组的区别：A–D 是「改哪个文件」，F 是「搬哪个写法」。宿主量化不同（iacop 吃 Q4_0/Q8_0、
> exabit 吃 Q8_0 激活），**文件不能直用**，但写法可以，且必须落到**我们的**量化（Q4_K 权重 / int8·k8v4 KV）。
> 每条都必须回答四样：判据用哪一列数、样本量、停机条件、成本。

| # | 手法 | 来源（宿主） | 我们落到哪 | 判据 / 样本 / 停机 / 成本 | 现状与判决 |
|---|---|---|---|---|---|
| **F1** | **载入暂存**：把每轮的权重 global load 先攒进寄存器，再统一写 LDS（把「1 载入→1 写」变成「N 载入→N 写」） | iacopPBK `matmul/mmq.cuh` 的 `GFX906_LOAD_TILES_Q8_0_ASYNC` / `_LDS_LEGACY`（**Q8_0**） | `mmq-load-tiles.cuh:711` 的 `ggml_cuda_mmq_load_tiles_q4_K`（dp4a 分支） | **判据 = ISA 的 `s_waitcnt` 与 `global_load`/`ds_write`/`v_dot4` 计数 + 2K/8K prefill 的 2×CV**；样本 = 每个 arm n≥3；停机 = 开窗时 1 次重启；成本 = 1 次全量重编（≈3 min，无 GPU） | **已拿、已判否（W1037，`P428`）**：编译通过（`-DSTRATA_GFX906_MMQ_STAGE`），ISA 实测 **`s_waitcnt` 6192 → 6165（−0.44%）**，`global_load` 3788 / `ds_write` 289 / `v_dot4` 5184 **逐项相同** ⇒ 编译器本来就把 8 次载入排到一起了（`STEP = nrows×nwarps = 4×4 = 16`，`I = 128` ⇒ **8 轮**），手工暂存只省 27 条等待。**期望 <1%，低于 2×CV，不开窗**；代码留在 `gfx906/port-all` 默认关 |
| **F2** | **DPP 归约**：`v_mov_b32_dpp` 的 xor1/2/4/8 代替 `ds_bpermute`/`__shfl_xor` | iacop `gfx906-common.cuh`；skyne98 实测 1778 vs 906 Gxchg/s | `native_router.cu` 三处归约 + top-k 交换（A1）；`qsa_decode_attn.cu` / `qsa_pattn.cu` 的 softmax（A3） | bitwise（同操作数对、同序）⇒ 只判速度；样本 n≥3；停机 1 次重启；成本 0（已在 pa1 里） | **已拿（A1/A3），待窗口**：`STRATA_GFX906_ROUTE_DPP` / `STRATA_GFX906_ATTN_DPP`，开关在 pa1 二进制里可见（`strings` 5/5） |
| **F3** | **half-warp 32 线程派发**：小矩阵（MoE、batch=1）用 32 lane 而不是 64 lane，减少半个 wave 的空转 | iacop `mmvq.cu`（`Q4_0/Q4_1/Q8_0` 的 warp 协作 MMVQ） | decode 的 MMVQ / MoE 小矩阵；**prefill 的 MMQ 是 tile 化的，用不上** | 判据 = decode ms/窗（**只设「不劣化」门**，2026-11-02 定：单流 decode 已在地板，收益不作成功判据）；样本 n≥5；停机 1 次重启；成本 ≈0.5 人日 | **不拿（判不适用）**：① gfx906 只有 wave64，32 lane 意味着半个 wave 空转，而 iacop 的收益来自「小矩阵下少一次归约」；② 我们的 decode 已经在 70.7 tok/s 的地板上（`§0.2` 第 1 条硬约束），这一条最多改 decode，按现行验收口径**没有收益可记** |
| **F4** | **预量化直喂**：norm/epilogue 直接吐 Q8_1，MMQ / MMVQ 不再自己量化激活 | exabit `fused norm 直吐 Q8_1`；iacop `fused/mmq-prequantized.cuh`（**Q8_0 激活侧**） | 与我们 `STRATA_QFUSE` 同题；要动的是 MoE 预填的激活量化链 | 判据 = prefill 2×CV + KL（改的是量化发生的位置，不是精度）；样本 n≥3；停机 1 次重启；成本 3–5 人日 | **不拿（前置已否）**：`B3` 的前提被 `P421` 否掉（decode 的整数点积不是 ALU-bound，A0 实测零结果）；且这条真正省钱的地方是「省掉一次 12 MB 级的激活搬运」，只在 `wait copy` 相位可见——我们的 `wait copy` 在 2.5K 只占 1.2%（`§0.1`）⇒ **分母不够** |

**F 组的一句话**：**这四条里只有 F2 值得测（已在 pa1），F1 已用 ISA 判否，F3 被验收口径判不适用，F4 被前置判否。
「能拿的都拿了」这句话现在有证据——证据不是我说拿得动，而是编译日志与指令计数。**
"""

anchor = "## 5 k8v4 与 int8 的成本模型"
assert anchor in s
s = s.replace(anchor, F.strip("\n") + "\n\n" + anchor, 1)

# 在 §4.0 的排序表里补一行指针，避免「手法」只活在附录
old = "| A4 逐文件 max-ilp | 构建脚本 | G3 只有性能 | 中性~+2% | 与任一车同发 |"
new = old + "\n| **F1 载入暂存** | 1 个宏 + 8 轮循环 | **ISA 计数 + G3** | 已判否：−0.44% waitcnt | 不做（`P428`） |\n| F3 half-warp 派发 / F4 预量化直喂 | 0.5–5 人日 | 见 F 组 | 见 F 组 | 判不适用 / 前置已否 |"
assert old in s
s = s.replace(old, new, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("PORT_PLAN: F 组已加入，§4.0 已补指针")
