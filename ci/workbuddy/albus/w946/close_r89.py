# -*- coding: utf-8 -*-
"""W946b: R89 closed by source reading — our prompt attention is already gather-only."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
EV = (" 【W946 实证 2026-11-04 16:1x｜A 级源码】**判否（已经是目标形态）**。读 `src/kernels/cuda/qsa_prompt_attn.cu:120-200`："
      "`prompt_attn_kernel` 里 `n = steps[qi*kStepCount + kStepWidth]`（该 query 的**选中 cell 数**）、"
      "`ids += qi*cap`（每 query 的**选中列表**）、主循环 `for (c0=0; c0<n; c0+=CH)` 内 `cell = ids[c0+c]` 再经 `page_table` 映射 "
      "⇒ **只读选中 cell（gather-only），不是扫全量**。furnace 的 +85% 是 dense→sparse，我们早已是 sparse，无可移植。"
      "W926 的耗时指数 1.20 也由此解释：indexer 部分 O(n) + core 部分 O(选中的 2048) 混合。"
      "剩余 attn 空间只剩**效率**（1.5-2.1 TFLOPS = FP32 峰 11-16%，R46），不是读得太多。")

with io.open(P, encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")

out, changed = [], []
for ln in lines:
    if "\t" in ln:
        f8 = ln.split("\t")
        if len(f8) >= 9 and f8[1] == "R89" and f8[7] != "DONE_NEG":
            f8[6] = "1"; f8[7] = "DONE_NEG"; f8[8] += EV; changed.append("R89"); ln = "\t".join(f8)
        elif len(f8) >= 9 and f8[1] == "R85":
            f8[8] += " 【W946b】R89 判否（我们已 gather-only）⇒ R85 的 attn 空间只剩 R46 的效率（11-16% 峰），不是读得太多。"
            changed.append("R85"); ln = "\t".join(f8)
    out.append(ln)

with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(out))
print("changed:", changed)
