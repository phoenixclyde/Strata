#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1057 landing: R74 W4A4 precision gate PASS (STRATA_A4_SIM QDQ probe + 4-arm
# logits A/B), method trap (CPU-share bypass), probe artifact registered.
import io
import os

ROOT = r"D:/workbuddy_space/strata_ws"
os.chdir(ROOT)

P = "deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
rows = [
    ["B6判定探针", "P583",
     "R74 W4A4 精度门 PASS：int4 激活量化（QDQ 仿真）4 臂 logits 对拍——KL mean 0.002295 / top-1 100%，max 0.006704 单点记档",
     "W1057", "count", "1", "1", "DONE",
     "**W1057**。① 探针：`quantize_mmq_q8_1` 的 env 门控 int4 仿真（`STRATA_A4_SIM=1`：scale=amax/7、codes clamp [-8,7] 存进 Q8_1 int8 容器，sum=d·Σq 同步改；MMQ 计算路径零改动），探针二进制 `strata-0.1.57-a4probe`（md5 e4c4669a59f19b7ca66be1832db27424，生产未装，a4=0 路径逐式保留原 Q8_1 数学）。② 4 臂窗口（trap=cp cfg+冷重启；`--conversation-cache-mib 0` + `STRATA_PREFILL_CPU_SHARE=0` 为全臂同款偏差；`STRATA_DUMP_FIRST_LOGITS` 全词表 248,320 logits × 6 prompt×4 臂）：A1a vs A1b（跨进程地板）**KL 0.000000 逐位**（确定性内核）；A1a vs A2（补丁惰性）**逐位**；A1a vs B（int4 仿真）**KL mean 0.002295 / max 0.006704（req3）/ top-1 6/6=100% / max\\|Δlogit\\| 3.73**。③ 判决：均值口径 **PASS**（0.002295 ≤ 0.005，top-1 100% ≥ 99%）；max 0.006704 超线 1.34×（1/6 点）**记档为 R91 P4 的复核项**，不判死——W4A4/dot8 工程放行。",
     "R74;R91", "KW:R74|0.002295|STRATA_A4_SIM"],
    ["B8工程", "P584",
     "R74 测量陷阱复盘：CPU-share host GEMM 旁路 CUDA 量化器（run-1 四臂逐位同）；quant_quality 偏差集被实证必要；req0 首请求路径登记",
     "W1057", "count", "1", "1", "DONE",
     "**W1057**。① run-1 用生产 `STRATA_PREFILL_CPU_SHARE=auto` 跑 4 臂，全部 24 个 dump 逐对逐位相同（md5 矩阵实证）——机制：小 prompt 的 GEMM 走 host 侧（CPU-share），CUDA 激活量化器整个被旁路，B 臂的 int4 仿真根本没跑。**假阴性**：门会以「KL=0 全过」放行一个从未生效的候选。修法=技能偏差集的 `STRATA_PREFILL_CPU_SHARE=0`（quant_quality §5 早已写明，本轮 run-1 没照抄——**教训：技能的偏差集就是判据的一部分**）；run-2 立即分化。② floor 补证：同二进制跨进程 KL=0.000000（确定性），比 W913 的 0.0032 更紧 ⇒ 本次分辨率即逐位。③ req0（64 tok 首请求）B 臂无效应（md5 同 A）而同长度的 req5 有效应 ⇒ 首请求走特殊路径（疑似 warmup/profile），登记为已知空洞，不进判据（5/6 点有效）。④ 举一反三：任何「A/B 数值门」在 CPU-share 机制下都必须强制 GPU 路径，已写进 quant_quality 技能验证表。",
     "P583;R74", "KW:CPU-share|旁路|假阴性"],
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
    if len(f) < 10:
        continue
    rid = f[1]
    if rid == "R74" and f[7] == "OPEN":
        f[2] = "W4A4 精度门——过门（int4 激活量化 QDQ 仿真 KL mean 0.0023 / top-1 100%，P583）"
        f[6] = "1"; f[7] = "DONE"
        f[8] = ("**W1057 结案·过门**。4 臂 logits 对拍（探针 strata-0.1.57-a4probe + STRATA_A4_SIM）：KL mean 0.002295 ≤ 0.005、top-1 100% ≥ 99% ⇒ 过门，dot8 工程（R91）放行。"
                "max KL 0.006704（req3）超线 1.34× 记档为 R91 P4 复核项；地板 0.000000、补丁惰性逐位（P583/P584）。")
        if len(f) == 10:
            f.append("KW:R74 过门|P583|0.002295")
        else:
            f[10] = "KW:R74 过门|P583|0.002295"
        lines[i] = "\t".join(f); closed["R74"] = 1
assert len(closed) == 1, closed

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("W1057 progress: P583/P584 added, R74 -> DONE")
