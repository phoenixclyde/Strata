import io

DIVE = io.open("albus/w1039/deep_dive.md", encoding="utf-8").read()
# turn its H1 into the report's §六 and demote its H2s
body = DIVE.split("\n", 1)[1].lstrip("\n")
body = body.replace("## 一、", "### 6.1 ").replace("## 二、", "### 6.2 ").replace("## 三、", "### 6.3 ")
body = body.replace("## 四、", "### 6.4 ").replace("## 五、", "### 6.5 ")
SECTION = ("## 六、深挖：DP4A 为什么反而慢（源码预算 + 对照项目 + 上网核）\n\n"
           "> 机主 09:44：「深度分析一下呢。尤其去对应的项目再看看怎么说的呢。照理会快啊。」\n\n" + body + "\n---\n\n")

R = "albus/w1039/reply.md"
s = io.open(R, encoding="utf-8").read()
anchor = "**产物**：`albus/w1039/reply.md`（本件）"
i = s.find(anchor)
assert i > 0, "footer anchor missing"
if "## 六、深挖" not in s:
    s = s[:i] + SECTION + s[i:]
    print("section 六 inserted")
io.open(R, "w", encoding="utf-8", newline="\n").write(s)

# ---------------- ledger ----------------
P = "deploy/PROGRESS.tsv"
ROWS = [
    dict(block="B6判定探针", id="P449",
         item=("DP4A 慢 7% 的机制算清了：每块只有 48/256 线程做量化、每 query 的 3072 个 q 元素被 64 个块各量化一遍；"
               "而 dot4 每 8 MAC 只省 3 条指令（2 dot4 + 3 收尾 vs 8 fma）⇒ 净 +20 条/cell"),
         source="W1039", kind="count", count="1", done="1", status="DONE",
         note=("**W1039 深挖（零停机，纯源码 + 预算）**。常数：`CHUNK=64`、`THREADS=256`、`WARPS=8`、`G=12`、`HD=256`、`NSC=4`、`top_k=2048` ⇒ 每 query **64 个块**（32 chunk × 2 KV 头）。"
               "**量化段**（`qsa_decode_attn.cu:234-247`）：`if (t < G*NSC)` 只有 **48 个线程**（19%），每线程串行 64 次 amax + 64 次 div/cvt ≈ 340–450 条指令，其余 208 线程等 `__syncthreads`。"
               "**分数段**：基线每 cell 每 lane = 12×8 FMA(96) + K 反量化(≈20，12 头共用) + reduce12(≈25) ≈ **130**；dp4a = 12×(2 dot4 + cvt + 2 mul)=60 + reduce12(25) ≈ **85**。"
               "每块 8 cell/ warp ⇒ 1040 vs 680；但 dp4a 要加 ≈400 周期的量化且被 syncthreads 隔开 ⇒ **1080 vs 1040（+3.8%）**，与实测 attn **+6.8%** 同量级同方向。"
               "**关键比值**：每 8 个 MAC，dot4 只省 3 条指令——4× 的算术密度被「每头一次 cvt+2mul 收尾」吃回 1.6×；再把 448 条/块的量化摊到 8 个 cell（56 条/cell）就变成净支出。"
               "⇒ 「照理会快」的前提是**转换被摊薄**，我们是**每块重来一次**、且每 query 冗余 64 份。"),
         ref="P447", kw="KW:量化段|每块"),
    dict(block="B6判定探针", id="P450",
         item=("对照项目与外证：iacop 的 Q 量化是**全线程 + 一块摊 nbatch_K 个 key + KV 本就是 Q8_0**；"
               "skyne98 同卡实测「热循环 QDQ 的 dot4 只有 fp32 的 0.34×、摊薄后才 1.67×」⇒ 我们的写法正落在慢的那一档；"
               "即使修好，天花板也只 −3.5%（16K）"),
         source="W1039", kind="count", count="1", done="1", status="DONE_NEG",
         note=("**W1039 上网核 + 本地源码对照（机主「尤其去对应的项目再看看怎么说的」）**。"
               "**① iacop `fattn-q8.cuh`**：`flash_attn_tile_q8_quantize_Q_to_shared` 用 `for (block_idx = tid; block_idx < ncols*blocks_per_col; block_idx += blockDim.x*blockDim.y)` —— **全线程参与**；一块覆盖 `nbatch_K`（128–256）个 key，量化一次摊销的分数工作量比我们大 2–4 倍；且它的 KV 原生 Q8_0，K 侧**根本不用反量化**。"
               "**② skyne98 `fp32-vs-qdq-dot-gfx906`（2026-02-21，同代 MI50）**：纯 fp32 5.95 TOPS；**热循环 QDQ int8-dot4 = 2.00 TOPS（0.34×）**；摊薄复用后 dot4 21.7 vs fp32 13.0（1.67×）。原文结论：*conversion paid every use ⇒ dot 不划算*。"
               "**③ 同站 `gfx906-dot4-dot8-exploration`**：sdot4 依赖链 21.7–22.3 TOPS、ILP4 43–44 ⇒ **硬件没打折，v_dot4 确实是 4 MAC/指令**，问题在喂数据的成本。"
               "**④ 外证**：llama.cpp 社区 2026-10 构建实测 `-ctk q8_0 -ctv q8_0` 在 64K 的 decode 只有 f16 的 56%，量化 KV 不等于更快。"
               "**天花板**：分数段只占 attn 一部分，attn 在 8K/16K 占 16.5%/17.2% ⇒ 即便分数段砍 45%，总 prefill 也只 −3.5%（16K）；而 `R104`（`--kv-grow`）一次 770+ 槽≈+10%。"
               "**判决：B1/B2 不再投人，DONE_NEG 收口**，机制与判据写进方案 §6.5 与本行。"),
         ref="P447;P449", kw="KW:0.34|天花板"),
]
s = io.open(P, encoding="utf-8").read()
add = []
for r in ROWS:
    if ("\t" + r["id"] + "\t") in s:
        print("skip", r["id"]); continue
    add.append("\t".join([r["block"], r["id"], r["item"], r["source"], r["kind"], r["count"], r["done"],
                          r["status"], r["note"], r["ref"], r["kw"]]))
if add:
    if not s.endswith("\n"):
        s += "\n"
    s += "\n".join(add) + "\n"
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("ledger +", [a.split("\t")[1] for a in add])

# ---------------- plan ----------------
PL = "deploy/W832_OPT_PLAN_V2.md"
t = io.open(PL, encoding="utf-8").read()
ADD = """
**六、深挖：为什么 DP4A 反而慢（`P449` / `P450`）。**
每 query 的选择上限 2048 ⇒ `n_chunks=32`、KV 头 2 ⇒ **每 query 64 个块**，而量化写在块内（`qsa_decode_attn.cu:234-247`）：
`if (t < G*NSC)` 只有 **48/256 个线程**，每线程串行 64 次 amax + 64 次 div/cvt（≈400 条），其余 208 线程等 `__syncthreads`。
分数段本身是省的：每 cell 每 lane 基线 ≈130 条（12×8 FMA + 反量化 + reduce12），dp4a ≈85（12×(2 dot4 + cvt + 2 mul) + reduce12），**省 35%**；
但加上 400 周期量化后每块 1080 vs 1040 ⇒ **净 +4%**，与实测 **+6.8%** 同量级。
**根子在两处**：① 每 8 个 MAC 只省 3 条指令（4× 密度被「每头一次 cvt+2mul 收尾」吃回 1.6×）；
② 量化每块重来一次，每 query 冗余 64 份。对照 iacop：`quantize_Q_to_shared` 全线程参与、一块摊 `nbatch_K`(128-256) 个 key、KV 原生 Q8_0 不用反量化。
外证（同代 MI50 实测，skyne98）：热循环 QDQ 的 dot4 **0.34×** fp32；摊薄复用后 **1.67×**。
**天花板**：分数段砍 45% ⇒ 总 prefill 16K 只 −3.5%，仍小于 `R104` 的 +10% ⇒ **B1/B2 收口，不再投入**。
判据（可复用）：引入 int8 dot 前先算「每 8 MAC 的净节省 − 每 cell 摊到的量化成本」，为负就别上。
"""
anchor = "**四、顺带修掉一个静默正确性洞（`P448`）。**"
i = t.find(anchor)
assert i > 0, "plan anchor missing"
if "**六、深挖：为什么 DP4A 反而慢" not in t:
    # insert after the 四 block: find the end of that block = the blank line before "---"
    j = t.find("\n---", i)
    t = t[:j] + "\n" + ADD + t[j:]
    io.open(PL, "w", encoding="utf-8", newline="\n").write(t)
    print("plan §六 appended")
