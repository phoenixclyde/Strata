#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1059 ledger landing #4: final sweep (R86 family, X6, P266, BLOCKED transitions).
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()

CLOSE = {
    "R86": ("DONE_NEG",
            "【W1059 收口】立项条件不成立（W832 §6.2 新21 自己写的门）：「R95 之后 且 down-only 端到端 ≥5% 才开工；默认不开工」——W1005 实测 down-only 上限 −2.6~−3.3%（intra/inter 串行结构上限），< 5% 门 ⇒ **不开工**。gu=Q4_K/Q5_K 侧早已实测净亏 1.0–3.9×（永不 repack）。口径=W1005 六长度档实测。",
            "KW:R86|W1005|不开工"),
    "R86-C1": ("DONE_NEG", "【W1059】随 R86 不开工一并收口：权重上传 repack 无宿主。口径=R86 判定行。", None),
    "R86-C2": ("DONE_NEG", "【W1059】随 R86 不开工一并收口：调度分派改造无宿主。口径=R86 判定行。", None),
    "R86-C5": ("DONE_NEG", "【W1059】随 R86 不开工一并收口：验收链无被验对象。口径=R86 判定行。", None),
    "X6": ("DONE_NEG",
           "【W1059 收口·code-census③】两开关全闲置（ROCm pinned 拷贝引擎只写不读 / exchange_rotate 未接线），按 W1035 §6.6 判读收口（与 D28 同口径）：接线成本 > 无实测收益 ⇒ 关。",
           "KW:X6|闲置"),
    "P266": ("DONE_NEG",
             "【W1059】采样归因的 gdb attach 通道与 P335 同墙（ptrace_scope=1 + 容器无 CAP_SYS_PTRACE，P336 实测双堵）⇒ attach 判死；归因改走 launcher 通道（rocprof 直启）与 LOGPOS 协议（本轮 P590/P591 即用该通道出数）。",
             "KW:P266|P335"),
}

BLOCKED = {
    "U2": "【W1059】转 BLOCKED-on-需求复核：端到端 +4.2% < 8% 预注册门（W983），R91 判否后同源 ROI 逻辑不捞；等整树统一（R117）后复核。",
    "U4": "【W1059】转 BLOCKED-on-机主：外发 PR 须机主批准且不产本机收益。",
    "G2": "【W1059】转 BLOCKED-on-R117：判据绑定 head 宽度 2560（统一宽度后自动满足）。",
    "G6": "【W1059】转 BLOCKED-on-R117：R42 异步族判死 + Amdahl 2.85%<3.2%，搭车整树统一。",
    "G4": "【W1059】转 BLOCKED-on-R89：归并 R89（32K attn 15-17% 上限同源），R89 出数后一并判。",
}

n_c = n_b = 0
out = []
for l in lines:
    f = l.split("\t")
    if len(f) >= 10:
        rid = f[1]
        if rid in CLOSE:
            st, det, kw = CLOSE[rid]
            f[7] = st
            f[6] = "1"
            f[8] += det
            if kw:
                if len(f) >= 11:
                    f[10] = kw
                else:
                    f.append(kw)
            l = "\t".join(f)
            n_c += 1
        elif rid in BLOCKED:
            f[7] = "BLOCKED"
            f[8] += BLOCKED[rid]
            l = "\t".join(f)
            n_b += 1
    out.append(l)

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("closed=%d blocked=%d" % (n_c, n_b))
