import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/.workbuddy/memory")
sec = """
## 01:4x（11-04）W926 · R64：attention 实测不是 O(L²)，且 k8v4 挡住 dp4a → 不做
- **口径纠正**：日志里 `qsa proj` 只占 **5.1%**，**`qsa attn` 是 14.8%**。此前把 proj 当 attention 是错的（W912/W924 都说过 14.9%，数字对但字段名错）。
- **【重要实测】attention 不是 O(L²)**：用日志里 7 个长度的 `qsa attn` 绝对耗时拟合 —— 7,929→99,382 tokens（长度 **12.5×**），时间 1,568→32,876 ms（**21.0×**）⇒ 指数 **1.20**，不是 2.0；对照 `qsa proj` 指数 **1.22**，**两者同阶**。原因：**QSA 是稀疏注意力**（top-k 选 KV，`qsa select` 只占 0.5%）。
- **占比稳定 15–19%**：8K **14.8%** / 22K 15.5% / 29K 18.6–19.6% / 32K **15.3%** / **99K 仍 15.3%** ⇒ **「长上下文 attention 成主战场」的通用经验在本引擎不成立**。真正随长度涨的是 `gemm gate/up`+`gemm down`（8K 合计 **34.6%**）⇒ 长上下文的靶子是 **GEMM/dequant**，不是 attention。
- **技术前提部分不成立**：`--kv k8v4` = K int8 + **V q4(4-bit)**，走 `KV_MODE==3`（注释自述 `K as int8, V dequantized to fp16`），该 TU 里 `dp4a|sdot4` 命中 **0**。而 `v_dot4_i32_i8` 只吃 int8×int8、`v_dot8_i32_i4` 是 i4×i4（W909 实跑证实）⇒ **V 这一半用不上任何 dot 指令**。要 int8 化只能改 k8v8（显存 +50%、精度重测）或把 Q 量化成 int8（现在 `const float* q`，改数值）。
- **Amdahl**：点积占 attention 40/50/70% ⇒ 端到端 **3.40/4.25/5.95%**，噪声门 3.2% ⇒ 上限刚好压门；对照 R51 先例（理论 4.15% → 实测 −6~−10%）⇒ 理论上限刚过门时实测大概率负。
- **判定 DONE_NEG**（三条理由任一都够）。保留观察：若将来换 k8v8（独立决策，牵涉显存+精度），本条重估，且那时 Q 量化可与 K 共用 scale。
- 进度 **93/156 = 59.6%**，主线 **93/128 = 72.7%**。队列 `… → ~~R64~~ → **R69**（#4590 penalty 窗口）→ R70 → R65 → R49 → R50 → R30′ → M3`。
- 产物：`deploy/W926_R64_ATTN_INT8.md`；`PROGRESS.tsv` R64(DONE_NEG)；`W832` 队列。零停服。
"""
with io.open("2026-11-03.md", "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
