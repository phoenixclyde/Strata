import io, shutil

# ---- recipe ----
P0 = "deploy/REBUILD_RECIPE.tsv"
shutil.copyfile(P0, P0 + ".bak_pa2")
s0 = io.open(P0, encoding="utf-8").read()
if "strata-0.1.57-pa2" not in s0:
    s0 = s0.rstrip("\n") + "\n" + (
        "strata-0.1.57-pa2\t234febafff8bcb502c2d462b3e5700c2\t43041712\tgfx906/port-all @ 未提交（W1037 未提交工作树）\t"
        "b11062 / 3cf03257\tb11062\tbuild-port2（/src=pr/port-all，/llama.cpp=llama.cpp）\t"
        "**OPT 接到预填派发**后的候选，未装机；注意它的 llama 仍是 b11062，不是在产的 b12180；见 P441\n")
    io.open(P0, "w", encoding="utf-8", newline="\n").write(s0)
print("recipe +1")

# ---- ledger ----
P = "deploy/PROGRESS.tsv"
shutil.copyfile(P, P + ".bak_pa2")
s = io.open(P, encoding="utf-8").read()
r = "\t".join([
    "B4上游移植", "P441",
    "窗口零效果的真因找到了：OPT 开关接在 _batch_rows/_slots 上，预填走 launch_chunks_batch（无 OPT 分支）；已接线并编译通过",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 立（更正 `P435` 的归因）**：`P434` 的零效果不是「打错文件」，是**接错了函数**。源码链：预填 → "
    "`qsa_decode_attn_batch`（`qsa_decode_attn.cu:1073`，`kernel=-1`）→ `launch_chunks_batch` → `STRATA_ATTN_CHUNK_SEL(M,pre)`（`:904-911`）"
    "= `attn_chunk_kernel<M>`，**这个模板没有 OPT 形参**；而 `STRATA_ATTN_OPT_{BATCH,STEP}` 只出现在 `:1170`（`qsa_decode_attn_batch_rows`）"
    "与 `:1365`（`qsa_decode_attn_slots`），两条都是变体路径（要 lane-cell / pre75 / swizzle 才进）。"
    "另外两条旁证：`qsa_prompt_attn_batch` 在 gfx906 **按构造 return false**（`qsa_prompt_attn.cu:2478-2480`）；"
    "`pattn_mode()` 在没设 `STRATA_PATTN_SM60` 时是 0（`qsa_pattn.cu:35`）⇒ ③ 也不走。"
    "**已接线**：在 `launch_chunks_batch` 的派发前加 OPT 分支（`opt != 0 && !lane_cell && !use_query_swizzle && kv_mode∈{3,1}` → "
    "`STRATA_ATTN_OPT_BATCH` + `return`，merge 由调用方做），编译通过 = `/data/bin/strata-0.1.57-pa2` `234febafff8bcb502c2d462b3e5700c2` / 43,041,712 B（未装机）。"
    "**它的 llama 还是 b11062**（port-all 的构建挂载），不是在产的 b12180 ⇒ 要测必须先把 port-all 按 b12180 配方重编。",
    "P435", "KW:launch_chunks_batch|接线"])

out = s.rstrip("\n") + "\n" + r + "\n"
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("ledger +1 (P441)")

# ---- W832 ----
P2 = "deploy/W832_OPT_PLAN_V2.md"
shutil.copyfile(P2, P2 + ".bak_pa2")
s2 = io.open(P2, encoding="utf-8").read()
a = "**382 条 / 已结 299 / 78.3%**（W1037 校正"
b = "**383 条 / 已结 300 / 78.3%**（W1037 校正"
assert a in s2
s2 = s2.replace(a, b, 1)
ADD = """
**十八、窗口零效果的真因：OPT 开关接在别的函数上（`P441`，更正 `P435` 的归因）。**
源码链只有一条：预填 → `qsa_decode_attn_batch`（`qsa_decode_attn.cu:1073`，`kernel=-1`）→ `launch_chunks_batch` →
`STRATA_ATTN_CHUNK_SEL(M, pre)`（`:904-911`）= **`attn_chunk_kernel<M>`，这个模板没有 OPT 形参**。
而 `STRATA_ATTN_OPT_BATCH` / `STRATA_ATTN_OPT_STEP` 只出现在 `:1170`（`qsa_decode_attn_batch_rows`）
与 `:1365`（`qsa_decode_attn_slots`）——两条都是**变体路径**，要 lane-cell / pre75 / swizzle 才进。
旁证两条：`qsa_prompt_attn_batch` 在 gfx906 **按构造 `return false`**（`qsa_prompt_attn.cu:2478-2480`，「the FP32 kernel runs」）；
`pattn_mode()` 不设 `STRATA_PATTN_SM60` 就是 0（`qsa_pattn.cu:35`）⇒ ③ 也不走。所以 `P435` 说的「预填走 ①②」是错的。

**已接线**：`launch_chunks_batch` 派发前插 OPT 分支（`opt != 0 && !lane_cell && !use_query_swizzle && kv_mode∈{3,1}` →
`STRATA_ATTN_OPT_BATCH` + `return`；merge 由调用方做），编译通过 ⇒ `/data/bin/strata-0.1.57-pa2` = `234febafff8bcb502c2d462b3e5700c2`
/ 43,041,712 B（**未装机**）。**注意**：它的 llama 还是 **b11062**（port-all 的构建挂载），不是在产的 b12180；
要测必须先把 port-all 按 b12180 配方重编一次（同一套 mount，把 `/llama.cpp` 换成 `llama-master`）。
"""
s2 = s2.rstrip("\n") + "\n" + ADD
io.open(P2, "w", encoding="utf-8", newline="\n").write(s2)
print("W832 +十八")

# ---- reply ----
P3 = "albus/w1037/reply.md"
s3 = io.open(P3, encoding="utf-8").read()
a3 = "**382 条 / 已结 299 / 78.3%**（W1037 校正；本轮 +16：`P425`–`P440`）。"
b3 = "**383 条 / 已结 300 / 78.3%**（W1037 校正；本轮 +17：`P425`–`P441`）。"
assert a3 in s3
s3 = s3.replace(a3, b3, 1)
s3 = s3.rstrip("\n") + "\n" + """
**19. 窗口零效果的真因：不是打错文件，是接错函数（`P441`，更正 §13/`P435`）。**
预填的调用链只有一条：`qsa_decode_attn_batch`（`:1073`，`kernel=-1`）→ `launch_chunks_batch` → `STRATA_ATTN_CHUNK_SEL(M,pre)`
（`:904-911`）= **`attn_chunk_kernel<M>`，没有 OPT 形参**；我们的 `STRATA_ATTN_OPT_BATCH/STEP` 只出现在 `:1170`
（`qsa_decode_attn_batch_rows`）和 `:1365`（`qsa_decode_attn_slots`）——变体路径，生产不进。
旁证：`qsa_prompt_attn_batch` 在 gfx906 按构造 `return false`（`qsa_prompt_attn.cu:2478-2480`）；`pattn_mode()` 默认 0（`qsa_pattn.cu:35`）。
⇒ §13 里「预填走 ①/②」是错的：② 直接拒绝、③ 没开，实际就是 ④，但 ④ 的派发里没有 OPT。
**已接线并编译通过**：`/data/bin/strata-0.1.57-pa2` = `234febafff8bcb502c2d462b3e5700c2` / 43,041,712 B（未装机）；
它的 llama 仍是 b11062，测之前要按 b12180 配方重编。
"""
io.open(P3, "w", encoding="utf-8", newline="\n").write(s3)
print("reply +19")
