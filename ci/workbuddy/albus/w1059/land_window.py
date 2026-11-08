#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1059 ledger landing #3: LOGPOS window results (P392/R101/profile finding).
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()

NEW = [
    "B8工程\tP590\tP392 LOGPOS 数值门 PASS（KL=0）：K10 整栈（#29953/#30168/#30553）与基线逐位等价，md5 同\tW1059\tcount\t1\t1\tDONE\t"
    "**W1059**。prefill-only LOGPOS 窗口（W824 §10 协议：STRATA_LOGPOS+TOPK=64+CPU_SHARE=0，kl_prop 口径，60 位置/臂）：**s010 vs s001b（-010 K10 整栈 vs -001 基线）KL mean 0.000000 / max 0.000000 / top1 60/60 / TSV md5 逐字节同**（156a2767…）⇒ 整栈数值逐位等价，P407 的「源码级等价（同一 launch_mul_mat_q 实例）」获**运行期实证**。配合 P390 速度免费（534.83/716.72 vs 532.76/714.89，2×CV 内）⇒ K10 栈（#29953 越界读修复+#30168/#30553）**可零代价拿**。#29953 的数值判定（P392 遗留）= 0 差异，闭案。\talbus/w1059/logpos_s010.tsv\tKW:P392|KL=0|K10",
    "B5本机缺口\tP591\tR101 判定：#31247 语义（Σx→d·Σq）已在本树，无需 cherry-pick；单变量实测差异非平凡（KL 0.104）\tW1059\tcount\t1\t1\tDONE\t"
    "**W1059**。①现状核实：本树 overlay quantize.cu:521 `sum = d * float(sum_q)` = **#31247 修复后形态**（上游 8fc0376「cuda: potential fix for Q8_1 correction sum」，已上网核实 1 文件 16+/14−）⇒ cherry-pick 为空操作。②单变量实测（sumx 探针 `strata-0.1.57-sumx`，STRATA_SUMX env 门控把 DS4/D2S6 块和退回 Σx 裸和，默认路径逐字保留；五臂窗口 sum1 vs sum0 同二进制单变量）：**KL mean 0.104091 / max 4.372991 / top1 58/60** ⇒ Σx↔d·Σq 的选择**不是平凡差异**——修正项（min 项）的输入和从精确和改量化和（或反之）在近零和块上被放大；#31247 的一致性修正在正确侧，本树已在正确侧。③R101 的旧判据（48-token 贪心指纹）已被 P388 废；本条以 LOGPOS 单变量替代收口。口径=同二进制 env 翻转对（sum0/sum1）+ 上游 commit 核实。\talbus/w1059/logpos_sum1.tsv\tKW:R101|0.104|8fc0376",
    "B8工程\tP592\tLOGPOS 窗口协议缺陷登记：首臂 expert-profile 生成态效应 KL mean 0.0044 / max 0.161（top1 全同）\tW1059\tcount\t1\t1\tDONE\t"
    "**W1059**。五臂窗口实测：s001a（首臂）vs s001b（同二进制第二臂）**KL mean 0.004404 / max 0.160985 / top1 60/60 / md5 不同**——配置带 `--expert-profile /src/data/expert-profile.bin --expert-profile-save /data/profiles/q4kxl-learned.bin`（共享 /data 挂载，profiles/ 目录 mtime=窗口首臂时刻），首臂走 profile 生成态、后臂走加载态，logit 分布随之改变（argmax 不变）。**协议修正**：LOGPOS/数值窗口的地板对必须用「profile 已就位后的第二臂 vs 第三臂」，或先空跑一臂暖 profile；首臂不得进地板对（本轮 floor 对 s001a/s001b 因此不为 0，已按污染解读而非内核噪声）。跨容器确定性另有实证：s001b vs s010（不同二进制）逐字节同 ⇒ 内核确定性成立。\talbus/w1059/kl_cmp.py\tKW:LOGPOS|profile|0.0044",
]

CLOSE = {
    "P392": ("DONE", "见 P590：KL=0 整栈等价，#29953 数值判定闭案。", "KW:P392|P590"),
    "R101": ("DONE", "见 P591：#31247 已在本树（d·Σq），无需 cherry-pick；单变量差异 KL 0.104 实测。", "KW:R101|P591"),
    "P335": ("DONE_NEG",
             "【W1059】profiler attach 实测失败的处置=不依赖 attach：rocprof 以 launcher 身份重启引擎直接采（W942 §7 流程），ptrace 路径双不通（ptrace_scope=1 + 容器无 CAP_SYS_PTRACE，P336 行实测）⇒ attach 通道判死，用 launcher 通道。",
             "KW:P335|ptrace"),
}

n_new = 0
out = []
for l in lines:
    f = l.split("\t")
    if len(f) >= 2 and f[1] in CLOSE:
        st, det, kw = CLOSE[f[1]]
        f[7] = st
        f[6] = "1"
        f[8] += det
        if len(f) >= 11:
            f[10] = kw
        else:
            f.append(kw)
        l = "\t".join(f)
    out.append(l)
out += NEW
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("added=%d closed=%d total=%d" % (len(NEW), len(CLOSE), len(out)))
