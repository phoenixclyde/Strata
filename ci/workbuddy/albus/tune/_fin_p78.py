# -*- coding: utf-8 -*-
"""把 P78 (STRATA_HC_Q8=1) 的证据写全。"""
import io, shutil, time

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
shutil.copy2(REG, REG + ".bak_p78_" + time.strftime("%Y%m%d_%H%M%S"))

EV = (
    "【W777 2026-10-23 实测采纳】0.1.48 新开关：hyper-connection 投影按 8-bit 读。"
    "上游源码 native_dense.cpp:49 原文 'also on for gfx1151 (Strix Halo, STRATA_HC_Q8=0 turns it off), "
    "off elsewhere' => gfx906 默认关，但可显式开。"
    "同口径 A/B（唯一 nonce、reused=0、5 runs/档，L 档 2 runs，99,381 token）："
    "prompt S 407.5->410.2 (+0.66%)、M 483.7->486.6 (+0.60%)、L 462.4->465.5 (+0.67%)，**三档一致 +0.6~0.67%**；"
    "decode S 59.4->62.4 (+5.0%)、M 60.1->61.3 (+2.0%)、L 38.9->41.5 (+6.7%，该档仅 32 token，分辨率不足)。"
    "副作用（正面）：HC 权重省显存 => expert_slots 9732->9901 (+169 槽，+1.7%)，vram_free 640->642。"
    "副作用（需记账）：near-tie 数值变化，上游 release note 明写 'Answers are not bit-identical'；"
    "回退 = STRATA_HC_Q8=0。"
)

lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
out, hit = [], False
for ln in lines:
    if ln.startswith("P78\t"):
        f = ln.split("\t")
        assert len(f) == 11, len(f)
        f[3] = "1"
        f[5] = "ADOPTED"
        f[9] = EV
        f[10] = "采纳：三档 prompt 一致 +0.6~0.67%，decode +2~5%，槽位 +1.7%；near-tie 数值变化已知"
        ln = "\t".join(f)
        hit = True
    out.append(ln)
assert hit
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("P78 updated, evidence len", len(EV))
