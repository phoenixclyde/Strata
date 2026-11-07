import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/deploy")

lines = io.open("PROGRESS.tsv", encoding="utf-8").read().split("\n")
hit = 0
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) == 10 and f[1] == "R64":
        f[6] = "1"; f[7] = "DONE_NEG"
        f[8] += (" 【W926 实测 2026-11-04 01:3x｜零停服】**三条理由任一条都够，判不做**。"
                 "**① 纠口径**：日志里 `qsa proj` 只占 5.1%，**`qsa attn` 是 14.8%**（此前抓 proj 当 attention 是错的）。"
                 "**② 决定性实测：attention 不是 O(L²)**——7 个长度的 `qsa attn` 耗时拟合指数 **1.20**（7,929→99,382 tokens，长度 12.5× 时间 21.0×），"
                 "对照 `qsa proj` 指数 1.22 ⇒ 两者同阶；原因是 **QSA 稀疏（top-k 选择，`qsa select` 仅 0.5%）**。"
                 "**占比稳定 15–19%：8K 14.8% / 22K 15.5% / 32K 15.3% / 99K 15.3%** ⇒ **「长上下文 attention 成主战场」在本引擎不成立**。"
                 "**③ 技术前提部分不成立**：`--kv k8v4` = K int8 + **V q4(4-bit)**，走 `KV_MODE==3`（注释自述 `V dequantized to fp16`），该 TU 里 dp4a/sdot 命中 **0**；"
                 "而 `v_dot4_i32_i8` 只吃 int8×int8、`v_dot8_i32_i4` 是 i4×i4（W909 实跑过）⇒ **V 这一半用不上任何 dot 指令**。"
                 "要 int8 化只有两条路：改 k8v8（显存 +50%、精度重测）或把 Q 量化成 int8（现在 `const float* q`，改数值）。"
                 "**④ Amdahl**：点积占 attention 40/50/70% ⇒ 端到端 **3.40/4.25/5.95%**，噪声门 3.2% ⇒ **上限刚好压在门上**；"
                 "对照 R51 的先例（理论 4.15% → 实测 −6~−10%）⇒ 理论上限刚过门时实测大概率负。"
                 "**保留观察**：若将来换 k8v8（独立决策），本条要重估。**副产品**：真正随长度涨的是 `gemm gate/up`+`gemm down`（8K 合计 34.6%）⇒ 长上下文的靶子是 GEMM/dequant 不是 attention")
        lines[i] = "\t".join(f); hit = 1
io.open("PROGRESS.tsv", "w", encoding="utf-8").write("\n".join(lines))
print("R64 -> DONE_NEG:", hit)

p = "W832_OPT_PLAN_V2.md"
s = io.open(p, encoding="utf-8").read()
old = ("> **执行顺序（2026-11-04 00:3x 修，`W925`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ → ~~R61~~ → ~~R60~~ → ~~R58~~ → "
       "~~R63 已结（Amdahl 重算端到端仅 1.74% < 3.2% 门，计算阶段判死）~~ → **R64**（attention int8 点积）"
       " → R69 → R70 → R65 → R49 → R50 → R30′ → M3**")
new = ("> **执行顺序（2026-11-04 01:3x 修，`W926`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ → ~~R61~~ → ~~R60~~ → ~~R58~~ → ~~R63~~ → "
       "~~R64 已结（attention 实测不是 O(L²)、占 15% 稳定；k8v4 挡住 dp4a；上限 3.4–4.3% 压门，不做）~~ → **R69**（`#4590` penalty 窗口）"
       " → R70 → R65 → R49 → R50 → R30′ → M3**")
assert old in s, "order not found"
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8").write(s)
print("W832 updated")
