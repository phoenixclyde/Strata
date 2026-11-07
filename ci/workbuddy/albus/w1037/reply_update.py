import io

P = "albus/w1037/reply.md"
s = io.open(P, encoding="utf-8").read()

a = "**369 条 / 已结 286 / 77.5%**（W1037 校正；本轮 +3：`P425` / `P426` / `P427`）。"
b = "**373 条 / 已结 290 / 77.7%**（W1037 校正；本轮 +7：`P425`–`P431`）。"
assert a in s, "denom anchor"
s = s.replace(a, b, 1)

ADD = """
**10. 手法四条：把「能拿」变成指令计数（机主追问后的补账，`P428`–`P431`）。**
四条逐条落进 `PORT_PLAN §4.F`，每条带「判据 / 样本 / 停机 / 成本」：

| # | 手法（宿主） | 我们的落点 | 结果 |
|---|---|---|---|
| F1 | 载入暂存（iacop，Q8_0 载入软件流水） | Q4_K dp4a 分支 `mmq-load-tiles.cuh:711` | **编译通过、ISA 判否**：`s_waitcnt` 6192 → **6165（−0.44%）**，`global_load` 3788 / `ds_write` 289 / `v_dot4` 5184 **逐项相同** ⇒ 期望 <1%，不开窗 |
| F2 | DPP 归约（iacop `gfx906-common.cuh`） | A1 router + A3 softmax（pa1 里） | bitwise，随窗口一起测 |
| F3 | half-warp 32 线程派发（iacop `mmvq.cu`） | decode MMVQ / MoE 小矩阵 | **判不适用**：gfx906 只有 wave64，32 lane 空转半个 wave；decode 已在地板、收益不作成功判据 |
| F4 | 预量化直喂（exabit norm 直吐 Q8_1 / iacop `mmq-prequantized`） | 与 `STRATA_QFUSE` 同题 | **前置已否**：B3 前提被 `P421` 否掉；`wait copy` 在 2.5K 只占 1.2%，分母不够 |

F1 的机制值得记住：`threads_per_row = MMQ_ITER_K/(4*QR4_K) = 16`、`nrows = 64/16 = 4`、`nwarps = 256/64 = 4`
⇒ `STEP = nrows*nwarps = 16`、`I = 128` ⇒ 环路**只有 8 轮**，`#pragma unroll` 之后编译器本就把 8 次载入排到一起，
手工暂存没有可重叠的余量。**「这套写法在别人那儿有用」和「在我们这条固化配置上有用」是两个命题**，能分开它们的只有计数。

**11. 两处补账：最新版核对到位、0.9.0 的尾巴收口（`P429` / `P430`）。**
① 上一轮拿 `ref/llama_b12169` 当「最新」是**错的对照物**。本轮直接取 master
`bcb0152876e8f0b684ba70d3defcab6cdf35adb5`（2026-11-06T22:42:46Z，距今约 8 小时），
其 `mmq-config-gcn.cuh`（HTTP 200 / 26,167 B / 256 行）与 pin 的同名文件 **`diff` 为空**，Q4_K 的 J 上限仍是 64
⇒ `P426` 的判否在**真 master** 上成立；顺带说明这 6.5 周上游没动过 gfx906 的 MMQ 表。
② `R100`（0.9.0 整树 / b12110）此前只留下「K10 免费」这一句，**没有处置**。本轮写成处置：
K10 = 534.83 / 716.72 vs 在产 532.76 / 714.89 ⇒ **+0.39% / +0.26%**（2×CV 内）；唯一实质修复 `#29953` 是越界读，
而我们的热路径自带 128 块余量（`P407`）⇒ 对我们是 no-op。**判不采用**；若要「跟上游对齐优先于收益」，一次重编 + 一个窗口即可。
"""

s = s.rstrip("\n") + "\n" + ADD
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("reply.md: denom + §10 + §11")
