#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039: three ledger rows -- the reduce12 confound, the common-mode error structure, the pa7 build."""
import io

P = "deploy/PROGRESS.tsv"
rows = [
    ("B6判定探针", "P457",
     "归约混淆：所有 OPT 臂跑的是 REDUCE12 版内核，而生产跑的不是 —— DP4A / F16D 的数值判决全是「两个改动一起比」",
     "W1039", "count", "1", "0", "OPEN",
     "**W1039 源码核实（`qsa_decode_attn.cu:1230-1256`）**：`if (const int opt_sw = gfx906_attn_opt(); opt_sw != 0)` "
     "之后 `STRATA_ATTN_OPT_DISPATCH_SWZ` 的宏体固定是 `attn_chunk_kernel<M, false, true, true, O>`，**第 4 个模板实参 "
     "REDUCE12 恒为 true**；而 ctl 走 `if (reduce12) ... else attn_chunk_kernel<M,false,true>`，`reduce12` 取自 "
     "`STRATA_GFX906_ATTN_REDUCE12`，生产 config 的 9 个 env 里**没有这个键**（容器内 `grep -c` = 0）。"
     "⇒ 到目前为止每一个「开关 vs 对照」的数值门都同时换了点积指令**和**归约方式（12 次 warp_sum ↔ 12-in-16 打包归约），"
     "所以 `P453`/`P456` 的 KL 不能归因到 DP4A 或 F16D 任一者，只能归因到「这两处一起变」。"
     "判据：跑 `STRATA_GFX906_ATTN_REDUCE12=1`（**只改一个 env、不动二进制**）对 ctl；KL≈0.038 ⇒ 归约是共因，"
     "KL=0 ⇒ 归约无辜，转 pa7 的 CTLREAD / F16Q 两位继续剥。",
     "P453;P456", "KW:REDUCE12|归约"),

    ("B6判定探针", "P458",
     "两臂误差**共模**：相关 0.70、幅度分布重合 ⇒ 不是位宽舍入，是同一处结构差；据此撤回 P454 的「int8 步长」归因",
     "W1039", "count", "1", "1", "DONE",
     "**W1039 逐点结构分析（`error_structure.py` 读已有 4 份 tsv，零窗口）**：int8 臂 |Δlogp(target)| 中位 **0.01769**、"
     ">0.01 占 **54.41%**；fp16 臂中位 **0.01930**、>0.01 占 **55.22%** —— 两臂幅度分布几乎重合；逐点相关 **0.6965**"
     "（signed 0.5456），两臂同时 >0.001 的位置 **3247/4995**。而地板臂（同二进制、两次独立容器）**逐位相同**"
     "（KL 0.00000 / top-1 100.00%），所以共模不是环境噪声。"
     "⇒ 若误差来自各自位宽的舍入，fp16（q 误差 0.03%）应比 int8（1.3%）小一个数量级，实测相等 ⇒ **共模**。"
     "据此撤回 `P454` 的机理（margin 数据仍有效：322 个改动、234 个是「第一名掉到第二名」、间隔 p50 0.191 nat），"
     "改记为「待 `P457` 的归约 / 读法剥离定位」。",
     "P454;P456", "KW:共模|0.6965"),

    ("B4上游移植", "P459",
     "pa7 建成：两个诊断位（bit4 CTLREAD = 基线算术走 OPT 读法；bit5 F16Q = fp16 查询 + fp32 fma），八开关全在册，窗口脚本就位",
     "W1039", "count", "1", "1", "DONE",
     "**W1039**。pa7 = `f04b91a6ebcbc649449632c39e8fdf01` / 43,576,168 B / 0 FAILED；`strings` 八项全 1"
     "（DPP / DP4A / LDS_PAD / F16D / CTLREAD / F16Q / REDUCE12 + 一条「bits 16/32 只支持 swizzle 路径」的警告串）。"
     "顺带把「bits 16/32 在没有 swizzle 时静默跑基线」改成打印一次警告（`P448` 那类静默洞的同一手法）。"
     "窗口：`gate3.sh`（phase1：ctl + `REDUCE12=1`，**不换二进制**，一次停起约 9 min）、"
     "`gate4.sh`（phase2：pa7 + CTLREAD / F16Q，约 9 min），控制臂复用 `g2_A.tsv` 与 `g3_A2.tsv`。"
     "本轮累计重启 11 次、停机 1779 s。",
     "P448;P456", "KW:pa7|诊断位"),
]

with io.open(P, "a", encoding="utf-8", newline="\n") as fh:
    for r in rows:
        fh.write("\t".join(r) + "\n")
print("appended %d rows" % len(rows))
for r in rows:
    print("  %s  verdict=%-4s cols=%d" % (r[1], r[7], len(r)))
