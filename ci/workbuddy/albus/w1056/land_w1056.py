#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1056 landing: R116 microbench verdict (gate FAIL -> DONE_NEG), queue reorder
# (code-related + prerequisites first, per 2026-11-08 directive).
import io
import os

ROOT = r"D:/workbuddy_space/strata_ws"
os.chdir(ROOT)

P = "deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
rows = [
    ["B6判定探针", "P581",
     "R116 微基准判否：同访问面 dot4 三臂全 <1.3x 门——上界（P 预量化）1.264x、诚实臂（含 P 量化）1.022x、V-int8 臂 1.248x",
     "W1056", "count", "1", "1", "REJECTED",
     "**W1056**。微基准 `albus/w1056/pv_micro_r116.cu`：生产形状 fold（CHUNK=64×G=12×HD=256，Q4_0 V 池 18B/32 值，thread t 拥有 dim t，cell-major P in LDS，4-cell V 组载）对拍 dot4 三臂，3 run×5 trial 交错（arm 轮转抵消漂移）。**A_fp32=0.0270 ms/chunk（CV 9%，三 run 均值 0.0270/0.0270/0.0270）；B_dot4_pre=0.0214（1.264x）；C_dot4_live=0.0264（1.022x）；D_dot4_v8=0.0216（1.248x）**。正确性：dot4 臂 vs CPU 同方案参考 rel_err 5.8e-8（逐位同构），合成 rel_rms 0.54%（真实数据预算 0.2603% 不变，P580）。**结构结论：PV fold 是访存/延迟瓶颈不是 ALU 瓶颈**——dot4 指令密度 4x 只转化 1.26x；P 在途量化再吃掉 23%（C vs B）。「V 读流量 ×2」在该形状下近免费（D vs B 差 1.3%）。预注册门「同访问面 >1.3x」不过 ⇒ 不接 OPT，R116 收口。",
     "R116;P580", "KW:R116|1.264|微基准"],
    ["B8工程", "P582",
     "唯一队列按「代码相关 + 前置项」重排（机主 2026-11-08 指令）：R74→R91→R101 提到第一梯队，治理项排后，队外代码候选入册",
     "W1056", "count", "1", "1", "DONE",
     "**W1056**。按机主指令重排 `W832 §0.1` 唯一队列：第一（代码+前置）R74（W4A4 精度门，R91 前置）→ R91（dot8 六阶段）→ R101（#31247 cherry-pick）；第二（prefill 代码手段）R46 > R64（前置=32K/131K 占比实测）> R60（前置=R59 KL 门），R85 验收随行；第三 R89→R95→R86（前置=R95 后且 ≥5%）；代码存量单列（P455/P481/P424/R63/G1-G10/D28/M2/K8/U2/U4/X3-X7/P1c）；治理 R80/R79/R81 排后。举一反三补查：R60 前置 R59、R64 前置占比实测、R86 前置 R95、R63 前置 R61——四条前置链在队内显式标注。",
     "R91;R74;R101", "KW:队列重排|R74|R91"],
]
for r in rows:
    assert len(r) == 11 and all("\t" not in x for x in r)
    assert not any(l.split("\t")[1] == r[1] for l in lines if l.count("\t") >= 9), r[1]
    whole = " ".join(r)
    for kw in r[10].replace("KW:", "").split("|"):
        assert kw in whole, (r[1], kw)
    lines.append("\t".join(r))

closed = {}
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) < 11:
        continue
    rid = f[1]
    if rid == "R116" and f[7] == "OPEN":
        f[2] = "R116：PV dot4 路线（P int8×V int8）——判否（预算 PASS 但微基准门 FAIL，P581）"
        f[6] = "1"; f[7] = "DONE_NEG"
        f[8] = ("**W1056 结案·判否**。① 误差预算 PASS：int8 rel_rms 0.2603%（P580）；② 微基准门 FAIL：同访问面 0.0270→0.0214/0.0264/0.0216 ms，"
                "上界 1.264x、诚实臂 1.022x、V-int8 臂 1.248x，全 < 预注册 1.3x 门（P581）。结构结论：PV fold 访存/延迟瓶颈，dot4 密度红利转化率 1.26x 封顶；"
                "R110→R116 的 k8v4 V 侧 dot 化整条线关闭。残余观察：V nibble→int8 流量 ×2 在该形状近免费（D vs B −1.3%），记录供后续 KV 布局决策引用。")
        f[10] = "KW:R116 判否|P581|1.264"
        lines[i] = "\t".join(f); closed["R116"] = 1
assert len(closed) == 1, closed

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("W1056 progress: P581/P582 added, R116 -> DONE_NEG")
