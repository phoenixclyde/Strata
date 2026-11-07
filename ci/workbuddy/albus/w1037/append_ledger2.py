import io, shutil

P = "deploy/PROGRESS.tsv"
shutil.copyfile(P, P + ".bak_w1037b")
s = io.open(P, encoding="utf-8").read()

rows = []

rows.append("\t".join([
    "B4上游移植", "P428",
    "手法①「载入暂存」在 Q4_K 上编译通过但 ISA 只省 0.44% 的 s_waitcnt：编译器本来就把 8 轮载入排在一起了",
    "W1037", "count", "1", "1", "DONE_NEG",
    "**W1037 立（把「能拿手法」这句话变成指令计数）**：iacop 的 Q8_0 载入暂存（`GFX906_LOAD_TILES_Q8_0_ASYNC`）搬到我们的 "
    "Q4_K dp4a 分支（`mmq-load-tiles.cuh:711`，补丁 `albus/w1036/mmq_stage_patch.py`，`-DSTRATA_GFX906_MMQ_STAGE`）。"
    "同一棵树编两遍（`-x hip --offload-arch=gfx906 --cuda-device-only -O3 -S`，实例文件 `template-instances/mmq-instance-q4_k.cu`）："
    "base `s_waitcnt` **6192** / staged **6165（−0.44%）**；`global_load` **3788**、`ds_write` **289**、`v_dot4_i32_i8` **5184** 逐项相同；"
    "两版 `.s` 都是 120,8xx 行（−13 行）。机制：`threads_per_row = MMQ_ITER_K/(4*QR4_K) = 16`、`nrows = 64/16 = 4`、`nwarps = 256/64 = 4` "
    "⇒ `STEP = 16`、`I = 128` ⇒ 环路**只有 8 轮**，`#pragma unroll` 之后编译器已把 8 次载入排到一起，手工暂存没有可重叠的余量。"
    "⇒ **期望收益 <1%，低于 2×CV，不开窗**；代码留在分支持上、默认关。副产物：`P424` 的「未通过编译验证」由此结清。",
    "P424", "KW:载入暂存|s_waitcnt"]))

rows.append("\t".join([
    "B10环境与版本", "P429",
    "「最新版 llama.cpp」核对到位：master HEAD bcb01528（2026-11-06 22:42）的 mmq-config-gcn.cuh 与 pin 逐字节相同",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 立（更正上一轮的对照物）**：上一轮拿 `ref/llama_b12169` 当「最新」，那不是最新。本轮直接取 "
    "`GET /repos/ggml-org/llama.cpp/commits/master` ⇒ **`bcb0152876e8f0b684ba70d3defcab6cdf35adb5`，2026-11-06T22:42:46Z**（距今 ~8 h）。"
    "按该 sha 取 `ggml/src/ggml-cuda/mmq-config-gcn.cuh`（HTTP 200，26,167 B，256 行）与 `ref/llama_3cf0325` 的同名文件 **`diff` 为空**；"
    "Q4_K 段仍是 `CASE(...,64/128, J∈{8,16,24,32,40,48,64}, ...)`，J 上限 64 未变。⇒ 「Q4_K 吃不到 J>64」在**真正的 master** 上仍然成立，"
    "`P426` 的判否不需要修改；同时说明这 6.5 周上游没有动过 gfx906 的 MMQ 表。",
    "P426", "KW:master|bcb01528"]))

rows.append("\t".join([
    "B10环境与版本", "P430",
    "R100 的尾巴收口：K10 栈（0.9.0 树 + MMQ 头 @2026-10-19）判「不采用」，理由是收益在 2×CV 内且 #29953 对我们 no-op",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 立（机主：「0.9.0 也没上，前面分析过一轮，最后像没动静」）**：那轮结论是 `P390` K10 = 534.83 / 716.72 vs 在产 001 = 532.76 / 714.89 "
    "⇒ **+0.39% / +0.26%**（K10 的 CV 0.26 / 0.15，两条都在 2×CV 内），`P391` 再证越到 `#29948` 就 −4.9%。"
    "本轮把它写成处置而不是悬着：**不采用**，三条理由——① 收益在噪声带内；② 唯一的实质修复 `#29953` 是越界读，而我们的热路径自带 128 块余量（`P407`，"
    "dense 最坏 16 块 < 128）⇒ 对我们是 no-op；③ 换整棵树＝一次全量重编 + 一次重验，收益不足以抵。"
    "**若机主要「跟上游对齐优先于收益」，这是一次重编 + 一个窗口的事，说一声就做。**",
    "P390", "KW:K10|不采用"]))

rows.append("\t".join([
    "B4上游移植", "P431",
    "手法清单收口：四条里 F2 已落地待测、F1 已用 ISA 判否、F3 被验收口径判不适用、F4 被前置判否；F 组已写进移植方案",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 立（机主：「你怎么拿手法。能拿你拿呀。入权威调优或者移植方案啊。」）**：`PORT_PLAN.md` 新增 **§4.F 组**，每条带"
    "「判据用哪一列 / 样本量 / 停机条件 / 成本」四样：**F1 载入暂存**（`P428`，ISA −0.44%，不开窗）、"
    "**F2 DPP 归约**（A1/A3，已在 pa1，待窗口）、**F3 half-warp 32 线程派发**（iacop `mmvq.cu`：gfx906 只有 wave64，32 lane 会空转半个 wave；"
    "而按 2026-11-02 的验收口径 decode 已在地板、收益不作成功判据 ⇒ **判不适用**）、"
    "**F4 预量化直喂**（exabit norm 直吐 Q8_1 / iacop `mmq-prequantized`：与 `STRATA_QFUSE` 同题，B3 前提被 `P421` 否掉，"
    "且 `wait copy` 在 2.5K 只占 1.2% ⇒ 分母不够）。§4.0 的排序表同时补了两行指针，避免手法只活在附录。",
    "R103", "KW:F 组|half-warp"]))

out = s.rstrip("\n") + "\n" + "\n".join(rows) + "\n"
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("appended 4 rows")
