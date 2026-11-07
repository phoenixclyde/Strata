# -*- coding: utf-8 -*-
"""重写 P26 evidence（上一次经 python -c 传递时反引号被 shell 吃掉）。
本文件用 Write 落盘、直接执行，不经 shell 引号解析。"""
import io, shutil, time

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
shutil.copy2(REG, REG + ".bak_w776c1b4_" + time.strftime("%Y%m%d_%H%M%S"))

EV = (
    "【W776-C1b 2026-10-22 实测并回滚】同口径 A/B（唯一 nonce、reused=0、5 runs/档）："
    "显式 21 -> S 406.5 / M 483.8；回滚默认 20 -> S 407.1 / M 484.3。"
    "**差异 0.1%，噪声内 => 无增益也无损失。**"
    "机理（0.1.47 新增上限）：启动行原文 "
    "\"CPU pool: 20 workers by default (22 physical cores, 44 logical processors; bounded by physical cores, one kept free)\" "
    "=> 上游有意留 1 个物理核；默认启动行 \"aux cpus: ... go to CPUs 22,21,43\" 证明 core 21 是 "
    "aux（prefill helper / GPU driver）的落点；显式 21 后 aux 只剩 \"CPUs 22\"，与 host 同物理核，"
    "而 --help 对 aux 的原文是 \"never a CPU that shares a core with a worker\"。"
    "**P26 原 calibrate（21=36.0 最优）在 0.1.42 成立、在 0.1.47 已失效**：那时默认就是 21，没有 one-kept-free 上限。"
    "=> 维持默认（不设 --pool-workers），把 aux 的余量留给上游。"
)

lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
out, hit = [], False
for ln in lines:
    if ln.startswith("P26\t"):
        f = ln.split("\t")
        assert len(f) == 11, len(f)
        f[9] = EV
        f[10] = "维持默认：显式 21 实测无增益（0.1%），且挤掉 aux 的专用核"
        ln = "\t".join(f)
        hit = True
    out.append(ln)
assert hit
assert "\t" not in EV
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("P26 evidence len =", len(EV))
