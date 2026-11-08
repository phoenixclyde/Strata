#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1056: rewrite the queue cell in W832 §0.1 (code-related + prerequisites first).
import io

P = r"D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()
start = s.find("| **唯一队列** |")
end = s.find("\n", start)
old = s[start:end]
assert old.count("**唯一队列**") == 1

new = (
    "| **唯一队列** | "
    "**第一（代码移植 + 前置门，2026-11-08 机主指令：优先推进代码相关的以及前置项）**："
    "**R74**（W4A4 离线精度门，不动内核——R91 的前置） → "
    "**R91**（dot8 接入 P1–P6，过门才动内核） → "
    "**R101**（#31247 cherry-pick，`quantize.cu` 的 DS4 分支同步改）　"
    "**第二（prefill 代码手段；R85 验收随行）**："
    "**R85**（长档 801→850 tok/s 端到端验收口径）→ 手段序 **R46**（attention 效率，上限 3.3×）> **R64**（Q.K int8；**前置**：32K/131K attention 占比实测）> **R60**（stream-k；**前置**：R59 KL≤0.005+top-1≥99%）　"
    "**第三**：**R89**（QSA prompt 只读选中 key）→ **R95**（小批 GEMM 残余=host/launch 侧）→ **R86**（Q5_1 down 布局重排；**前置**：R95 之后且 down-only 端到端 ≥5%，默认不开工）　"
    "**代码存量候选（队外 OPEN，按需捞入）**：P455（fp16 dot2 救 P454 层）· P481（解开 3 处编译期排除）· P424（MMQ load 管线误配核查）· R63（MLP 权重重排；**前置** R61）· G1–G10 / D28 / M2 / K8 / U2 / U4 / X3–X7 / P1c　"
    "**治理（排后）**：**R80**（ci/gate 三项 provenance）→ **R79**（重启后多轮会话完好）→ **R81**（窗口宽度 6→12）　"
    "**存量（不排期，随时可捞）**：R72 · R50 · R49 · R42 · R39 · R19 · R45　"
    "**W1032–W1052 已结**：R103 R104 R105 R106 R107(R107→AUDIT29 已执行) R108 R109 R111 R113 均为 DONE；R110 R112 R114 R115 为 DONE_NEG（判否，证据见各轮）；R99 R100 R102 亦 DONE_NEG（历史）。"
    "**W1055–W1056 追记**：R116 判否（预算 PASS 0.2603% / 微基准门 FAIL 1.264×，`P580`/`P581`），k8v4 V 侧 dot 化整线关闭。"
    "**AUDIT29 校正**：本格此前是 append-only 的堆栈（含已判否的 R110/R112 置顶、已结的 R106/R107 仍写作待办、断裂的嵌套 `**` 与 W1037 残段），现按账本重排；任何「重排/第 1 序」的历史文字都不再是现行排期。 | "
    "本节 + `§6.5` 各回写块；**AUDIT27 校正**；**W1056 重排（机主令）** |"
)
s = s[:start] + new + s[end:]
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("queue cell rewritten, new len", len(new))
