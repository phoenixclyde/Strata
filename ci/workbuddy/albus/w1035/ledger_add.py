#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1035: add the P407 ledger row and move the single-source denominator.

Rules obeyed:
  * backup before touching a long file (W1033 truncated AUDIT24 with one read+open expression)
  * never read and open-for-write in the same expression: read -> modify in memory -> write
  * the denominator exists exactly once (W832 §0.1) and must equal the value progress.py derives
"""
import io
import shutil
import sys

PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"

ROW = "\t".join([
    "B8工程",
    "P407",
    "P392 静态重估：#29953 只改缓冲区大小（tile 选择逐行等价），且我们的 MoE 预填已自带 128 块余量",
    "W1035",
    "count",
    "1",
    "1",
    "DONE",
    "**W1035 立**：① 生产树 = 修复前（`mmq.cuh:372` 仍是 `get_J_max`；`mmq.cu:137/206` 仍用它算 padding；"
    "上游 diff 的 `-` 块与本树 `mmq.cuh:1479-1500` 逐字相同）；② 补丁不改被选中的 tile：`ncols_opt`（dense `ne1≡ne11`、"
    "MoE 都是 `ne12`）与 `fallback`（`ne01%128!=0` ≡ `needs_fallback`）前后等价 ⇒ 同一 "
    "`launch_mul_mat_q<type,J,fallback>` 实例 ⇒ 数值应逐位相同（**源码级等价，未做运行期实测 ⇒ `P392` 仍 OPEN**）；"
    "③ 热路径本就不越界：`moe_mmq.cu:407 q8_bytes()` 固定 +128 块（= 最大 J），`gemm.cu:1282` / "
    "`prefill.cpp:1605` 都走它；残余暴露只有 ggml dense（`fallback=false` 时 ≤16 块 = 2304 B，仅 `ne11%8≠0`）"
    "与 MoE `ids`（`T*K` 无余量，≤252 B）；④ `-001` vs `-010` 的 KL 归因不到单条补丁（`-010` = 0.9.0 树 + 旧 mmq 头，"
    "混合树，同 `P389`）⇒ C 的实验只能按「整栈」解读。复现：`albus/w1035/mmq_pad_check.py`",
    "P392",
])


def main():
    prog = io.open(PROG, encoding="utf-8").read()
    if "\tP407\t" in prog:
        print("P407 already present")
        return 1
    shutil.copyfile(PROG, PROG + ".bak_w1035")
    lines = prog.rstrip("\n").split("\n")
    lines.append(ROW)
    out = "\n".join(lines) + "\n"
    io.open(PROG, "w", encoding="utf-8", newline="\n").write(out)
    print("PROGRESS.tsv +P407  (%d -> %d lines)" % (len(lines) - 1, len(lines)))

    plan = io.open(PLAN, encoding="utf-8").read()
    old = "| 进度分母 | **348 条 / 已结 266 / 76.4%**（W1034 校正；"
    new = "| 进度分母 | **349 条 / 已结 267 / 76.5%**（W1035 校正；"
    if old not in plan:
        print("!! §0.1 denominator line not found; plan untouched")
        return 2
    shutil.copyfile(PLAN, PLAN + ".bak_w1035")
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(plan.replace(old, new))
    print("W832 §0.1 denominator -> 349/267/76.5%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
