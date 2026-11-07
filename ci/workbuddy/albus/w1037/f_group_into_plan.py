import io, shutil

P = "deploy/W832_OPT_PLAN_V2.md"
shutil.copyfile(P, P + ".bak_w1037d")
s = io.open(P, encoding="utf-8").read()

OLD_HEAD = "**八、手法四条：一条用指令计数判否，一条已落地，两条按口径判不适用（`P428`–`P431`）。**\n机主追问「你怎么拿手法，能拿你拿呀」——把「能拿」变成可复查的计数，而不是形容词。四条逐条落进 `PORT_PLAN §4.F`："
NEW_HEAD = ("**八、手法四条：一条用指令计数判否，一条已落地，两条按口径判不适用（`P428`–`P431`）。**\n"
            "机主追问「你怎么拿手法。能拿你拿呀。入权威调优或者移植方案啊」——把「能拿」变成可复查的计数，而不是形容词。\n"
            "四条按**开条目必须的四样**（判据 / 样本量 / 停机条件 / 成本）逐条立在这里；同一份也写在 `PORT_PLAN §4.F`（移植侧视角）：")

OLD_TBL = """| # | 手法（来源宿主） | 落点 | 结果 |
|---|---|---|---|
| F1 | 载入暂存（iacop，Q8_0） | Q4_K dp4a 分支 `mmq-load-tiles.cuh:711` | **编译通过、ISA 判否**：`s_waitcnt` 6192 → **6165（−0.44%）**，`global_load`/`ds_write`/`v_dot4` **逐项相同**。机制：`threads_per_row=16`、`nrows=4`、`nwarps=4` ⇒ `STEP=16`、`I=128` ⇒ 环路**只有 8 轮**，`#pragma unroll` 后编译器已把 8 次载入排到一起，没有可重叠的余量 ⇒ 期望 <1%，不开窗 |
| F2 | DPP 归约（iacop / skyne98） | `native_router.cu`、`qsa_*attn.cu` | 已落地（A1/A3），bitwise，随窗口一起测 |
| F3 | half-warp 32 线程派发（iacop `mmvq.cu`） | decode MMVQ / MoE 小矩阵 | **判不适用**：gfx906 只有 wave64，32 lane 空转半个 wave；且按 2026-11-02 的验收口径 decode 已在地板，收益不作成功判据 |
| F4 | 预量化直喂（exabit / iacop `mmq-prequantized`） | 与 `STRATA_QFUSE` 同题 | **前置已否**：B3 前提被 `P421` 否掉；`wait copy` 在 2.5K 只占 1.2%，分母不够 |"""

NEW_TBL = """| # | 手法（来源宿主） | 落到我们的哪 | 判据 · 样本 · 停机 · 成本 | 判决与数 |
|---|---|---|---|---|---|
| **F1** | **载入暂存**：每轮权重 global load 先攒进寄存器，再统一写 LDS（「1 载入→1 写」变「N 载入→N 写」） | iacop `matmul/mmq.cuh` 的 `GFX906_LOAD_TILES_Q8_0_ASYNC`（宿主 **Q8_0**） → 我们的 `mmq-load-tiles.cuh:711` Q4_K dp4a 分支 | **判据** = ISA 的 `s_waitcnt`/`global_load`/`ds_write`/`v_dot4` 计数 + 2K/8K prefill 的 2×CV；**样本** n≥3；**停机** 开窗时 1 次重启；**成本** 1 次全量重编（≈3 min，无 GPU） | **已拿、已判否**（`P428`）。同树编两遍：`s_waitcnt` **6192 → 6165（−0.44%）**；`global_load` **3788**、`ds_write` **289**、`v_dot4_i32_i8` **5184** **逐项相同**；`.s` 120,870 → 120,857 行。机制：`threads_per_row = MMQ_ITER_K/(4·QR4_K) = 16`、`nrows = 64/16 = 4`、`nwarps = 256/64 = 4` ⇒ `STEP = 16`、`I = 128` ⇒ 环路**只有 8 轮**，`#pragma unroll` 后编译器已把 8 次载入排一起，手工暂存无余量 ⇒ **期望 <1%，低于 2×CV，不开窗**；代码留在分支默认关 |
| **F2** | **DPP 归约**：`v_mov_b32_dpp` 的 xor1/2/4/8 代替 `ds_bpermute`/`__shfl_xor` | iacop `gfx906-common.cuh`；skyne98 实测 1778 vs 906 Gxchg/s → 我们的 A1（router 三处归约 + top-k 交换）、A3（softmax） | **判据** = bitwise（同操作数对、同序）⇒ 只判速度；**样本** n≥3；**停机** 随窗口 1 次；**成本** 0（已在 pa1 里） | **已落地、本轮窗口在测**：`STRATA_GFX906_ROUTE_DPP` / `STRATA_GFX906_ATTN_DPP`，开关在 pa1 二进制里可见（`strings` 5/5） |
| **F3** | **half-warp 32 线程派发**：小矩阵用 32 lane 而不是 64 lane | iacop `mmvq.cu`（Q4_0/Q4_1/Q8_0 的 warp 协作 MMVQ）→ decode MMVQ / MoE 小矩阵；**prefill 的 MMQ 是 tile 化的，用不上** | **判据** = decode ms/窗，**只设「不劣化」门**（2026-11-02 定：单流 decode 已在地板，收益不作成功判据）；**样本** n≥5；**停机** 1 次重启；**成本** ≈0.5 人日 | **判不适用**：gfx906 只有 wave64，32 lane 会空转半个 wave；且 decode 已在 70.7 tok/s 地板 ⇒ 按现行验收口径**没有收益可记** |
| **F4** | **预量化直喂**：norm/epilogue 直接吐 Q8_1，MMQ/MMVQ 不再自己量化激活 | exabit「fused norm 直吐 Q8_1」；iacop `fused/mmq-prequantized.cuh`（**Q8_0 激活侧**）→ 与我们 `STRATA_QFUSE` 同题 | **判据** = prefill 2×CV + KL（改的是量化发生的位置，不是精度）；**样本** n≥3；**停机** 1 次重启；**成本** 3–5 人日 | **前置已否**：B3 的前提被 `P421` 否掉（A0 实测零结果，decode 整数点积不是 ALU-bound）；这条真正省钱处在 `wait copy`，而 2.5K 只占 **1.2%** ⇒ 分母不够 |"""

assert OLD_HEAD in s, "head anchor"
s = s.replace(OLD_HEAD, NEW_HEAD, 1)
assert OLD_TBL in s, "table anchor"
s = s.replace(OLD_TBL, NEW_TBL, 1)

# 九 的末句与机主 07:18 的新指令冲突（他定了「跟」），改成引用而不是留一个相反的判决
OLD9 = "⇒ 判**不采用**；若要「跟上游对齐优先于收益」，一次重编 + 一个窗口即可，等机主一句话。"
NEW9 = ("⇒ 当时判**不采用**；**机主 2026-11-07 07:1x 定「跟上游对齐优先于收益，只要不是负优化就跟」⇒ 该判决作废，改判「跟」**，"
        "执行见下一节（十）。")
if OLD9 in s:
    s = s.replace(OLD9, NEW9, 1)
else:
    print("WARN: 九 tail anchor missing")

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("W832 八 -> 四字段全表；九 末句改判")
