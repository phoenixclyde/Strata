import io, shutil

P = "deploy/W832_OPT_PLAN_V2.md"
shutil.copyfile(P, P + ".bak_w1037b")
s = io.open(P, encoding="utf-8").read()

# --- §0.1 denominator + queue -------------------------------------------------
a = "**369 条 / 已结 286 / 77.5%**（W1037 校正"
b = "**373 条 / 已结 290 / 77.7%**（W1037 校正"
assert a in s
s = s.replace(a, b, 1)

c = "**待点头开窗**（三臂 / 三次重启 / 约 5–8 min）"
d = ("**待点头开窗**（三臂 / 三次重启 / 约 5–8 min）；手法四条已按 `PORT_PLAN §4.F` 收口"
     "（F2 待测、F1 ISA 判否 `P428`、F3 判不适用、F4 前置已否 `P431`）；最新版核对到位（master `bcb01528` / 2026-11-06，`P429`）；"
     "R100 的 K10 尾巴处置为**不采用**（`P430`）")
assert c in s
s = s.replace(c, d, 1)

# --- §6.5 W1037 block: append 八 -------------------------------------------------
ADD = """
**八、手法四条：一条用指令计数判否，一条已落地，两条按口径判不适用（`P428`–`P431`）。**
机主追问「你怎么拿手法，能拿你拿呀」——把「能拿」变成可复查的计数，而不是形容词。四条逐条落进 `PORT_PLAN §4.F`：

| # | 手法（来源宿主） | 落点 | 结果 |
|---|---|---|---|
| F1 | 载入暂存（iacop，Q8_0） | Q4_K dp4a 分支 `mmq-load-tiles.cuh:711` | **编译通过、ISA 判否**：`s_waitcnt` 6192 → **6165（−0.44%）**，`global_load`/`ds_write`/`v_dot4` **逐项相同**。机制：`threads_per_row=16`、`nrows=4`、`nwarps=4` ⇒ `STEP=16`、`I=128` ⇒ 环路**只有 8 轮**，`#pragma unroll` 后编译器已把 8 次载入排到一起，没有可重叠的余量 ⇒ 期望 <1%，不开窗 |
| F2 | DPP 归约（iacop / skyne98） | `native_router.cu`、`qsa_*attn.cu` | 已落地（A1/A3），bitwise，随窗口一起测 |
| F3 | half-warp 32 线程派发（iacop `mmvq.cu`） | decode MMVQ / MoE 小矩阵 | **判不适用**：gfx906 只有 wave64，32 lane 空转半个 wave；且按 2026-11-02 的验收口径 decode 已在地板，收益不作成功判据 |
| F4 | 预量化直喂（exabit / iacop `mmq-prequantized`） | 与 `STRATA_QFUSE` 同题 | **前置已否**：B3 前提被 `P421` 否掉；`wait copy` 在 2.5K 只占 1.2%，分母不够 |

**九、两处补账。** ① **最新版核对到位**：上一轮拿 `ref/llama_b12169` 当「最新」是错的对照物。本轮取 master
`bcb0152876e8f0b684ba70d3defcab6cdf35adb5`（2026-11-06T22:42:46Z），其 `mmq-config-gcn.cuh`（200 / 26,167 B）与 pin 的
**`diff` 为空**，Q4_K 的 J 上限仍是 64 ⇒ `P426` 的判否在真 master 上成立，且这 6.5 周上游没动过 gfx906 的 MMQ 表。
② **R100 的尾巴收口**：K10 栈 = +0.39%/+0.26%（2×CV 内），唯一实质修复 `#29953` 对我们 no-op（`P407`，自带 128 块余量）
⇒ 判**不采用**；若要「跟上游对齐优先于收益」，一次重编 + 一个窗口即可，等机主一句话。
"""
s = s.rstrip("\n") + "\n" + ADD
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("W832 updated: denom, queue, W1037 block +8/+9")
