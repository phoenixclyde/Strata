#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1035: append the daily-memory entry (append-only) and bump the handoff SNAPSHOT round.

Both are two separate write paths on purpose: W1033 lost a file to a read+open in one expression.
"""
import io
import re
import shutil
import sys

MEM = ".workbuddy/memory/2026-11-07.md"
HANDOFF = "albus/w1034/HANDOFF.md"

ENTRY = """
## W1035 · 2026-11-07 02:2x–03:0x（P392 静态重估 + C 备跑 + 收工仪式机械化）

- **P392 的性质被改写（源码核实）**：上游 `#29953`「CUDA: fix MMQ out-of-bounds reads」（head `3070d927`）只改缓冲区大小与 `J_best` 的传递路径。生产树 `mmq.cuh:372` / `mmq.cu:137,206` 确认是 pre-fix；但补丁删掉的选 tile 循环与本树 `mmq.cuh:1479-1500` **逐字相同**，`ncols_opt`（dense `ne1≡ne11`、MoE 都是 `ne12`）与 `fallback`（`ne01%128!=0`）前后等价 ⇒ 同一 `launch_mul_mat_q<type,J,fallback>` 实例 ⇒ 数值应逐位相同。**源码级等价 ⇒ P392 仍记 OPEN**（纪律：只有源码阅读的写 OPEN）。
- **我们的热路径本就不越界**：`moe_mmq.cu:407 q8_bytes()` 固定 `+128 × sizeof(block_q8_1_mmq)`（= 最大 J），`gemm.cu:1282` / `prefill.cpp:1605` 都走它。用镜像内 250 条 gfx906 配置表算：Q4_K/Q5_K/Q5_1 最大 J=64、Q8_0=128；ggml dense 残余越界 ≤16 块 = 2304 B（仅 `ne11%8≠0`），MoE `ids` ≤252 B。真实形状 `ne11=1000/16384` 全部 `J_max==J_best`。
- **归因陷阱（第二次）**：`-001` vs `-010` 是混合树（0.9.0 树 + mmq 头@4c1004c），KL 归因不到单条补丁，同 `P389`。规则：单补丁归因必须「同树 + 单 patch」。
- **C 已备跑未执行**：三臂 `001` / `001b`（自一致地板）/ `010`，`quant_quality.py prompt`（批量 prefill + 全词表 float32 logits，20 个配对点）。命令行用镜像内 `engine_args()` 算出并逐字比对，三臂只差 exe 与 profile 落盘路径。预检 PASS（`001`=`5e63174d…`、`010`=`6de7b937…`、config `53ac61e0…`、ids/numpy 齐、stray qq=0）。安全：每臂独立一次性容器 + 停服后断言 `engines=0` 且 VRAM<2GB + 单臂 270 s timeout + 720 s wall guard + trap 回滚。偏差：`--kv fp16`、`CPU_SHARE=0`、`expert-cache 1500`、`max-context 1512`（三臂同 ⇒ 配对有效，但不含主机 CPU share）。
- **收工仪式机械化**：新增 `tools/round_ledger.py` 并接进 `round_close.py` HARD —— 从 HANDOFF `SNAPSHOT round=` 取轮次，要求 `albus/<round>/reply.md` + `PROGRESS.tsv` 有 source==round 的行 + 当日记忆提到该轮，缺一即 FAIL。起因：机主第三次问「每轮的四项报告呢 / 你的 CI/CD 呢」，而旧门只验报告质量、不验「这一轮有没有落账」。
- 账本 `P407`，分母 **349 / 267 / 76.5%**，`W832 §0.1` 已回写。生产 **0 重启 0 分钟停机 0 回滚**，`001`/`5e63174d`/config `53ac61e0`/`restarts=0`。
- **教训**：①「性能免费」≠「可以拿」，只含安全修复且被自家 padding 抵消的补丁收益是 0；②`q8_bytes()` 的 +128 块是没注释的隐式不变量，改它就把上游的坑搬回来；③门要覆盖「有没有做」，不能只覆盖「做得好不好」。
"""


def main():
    txt = io.open(MEM, encoding="utf-8", errors="replace").read()
    if "## W1035" in txt:
        print("memory already has W1035")
    else:
        with io.open(MEM, "a", encoding="utf-8", newline="\n") as f:
            f.write(ENTRY)
        print("memory appended (%d -> %d chars)" % (len(txt), len(txt) + len(ENTRY)))

    h = io.open(HANDOFF, encoding="utf-8", errors="replace").read()
    if "round=W1035" in h:
        print("handoff SNAPSHOT already W1035")
        return 0
    shutil.copyfile(HANDOFF, HANDOFF + ".bak_w1035")
    new = re.sub(r"round=W\d{4}", "round=W1035", h, count=1)
    if new == h:
        print("!! SNAPSHOT round not found")
        return 2
    io.open(HANDOFF, "w", encoding="utf-8", newline="\n").write(new)
    print("handoff SNAPSHOT -> round=W1035")
    return 0


if __name__ == "__main__":
    sys.exit(main())
