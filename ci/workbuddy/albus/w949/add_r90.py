# -*- coding: utf-8 -*-
"""W949: add R90 (llama.cpp baseline upgrade to b12099) to the ledger."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
EV = ("**W949 立（2026-11-04 16:1x，机主「换，而且换紧跟上游的 gfx906 专门版本」）**。"
      "**版本真相（W948，代码标志比对五棵树）**：furnace / exabit(merge-v0.7.0) / mx(b11553) 三家 gfx906 fork 的 mmq.cuh **都没有 get_J_max**，"
      "而我们 pin 有 ⇒ **三家基线上游都比我们旧**；真正新的是 **llama.cpp master b12099（2026-11-04）**，与我们 **587 行差异**。"
      "⇒ 换的对象不是 fork，是 **b12099 基线 + gfx906 补丁层**。"
      "**四步**：S1 下载 `ggml/src/ggml-cuda/` 全目录到 `~/strata166/ref/llama_b12099/`（只读，零风险）；"
      "S2 用它当 `STRATA_GGML_DIR`、**先关 `STRATA_MMQ_TAB`** 在新 build 目录编通（`build-r28` 与旧树不动）；"
      "S3 重做 mirror（`mul_mat_q_process_tile → DECL_MMQ_CASE`）+ 更新 CMake `_strata_mmq_tab_known` + 跑 `prefill_mmq_tab_test`（逐位）；"
      "S4 叠补丁层：repack(R86)、q8_1 cache(R87)、max-ilp(R49)。"
      "**已核**：上游 master **已有 `mmq-config-gcn.cuh`**（#27841，HTTP 200）⇒ 不必重搬；`q8_repack/` 仍是 fork 独有（404）⇒ repack 自己写。"
      "**回滚**：`STRATA_GGML_DIR` 指回 `~/strata166/llama.cpp`，生产引擎不动直到 S3 出二进制且数字不劣。")

row = ["B10环境与版本", "R90",
       "llama.cpp 基线升级到上游 b12099（2026-11-04）+ gfx906 补丁层（S1 下载 / S2 关 tab 编通 / S3 重做 mirror / S4 叠 repack+q8_1+max-ilp）",
       "W948 §2-§3", "count", "1", "0", "OPEN", EV, "W948;W946;W944"]

with io.open(P, encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")
while lines and lines[-1] == "":
    lines.pop()
lines.append("\t".join(row))
lines.append("")
with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(lines))
print("R90 added")
