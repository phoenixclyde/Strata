# -*- coding: utf-8 -*-
"""C1b: 回滚 P26(--pool-workers 21) -> 默认。证据：
 0.1.47 日志 `CPU pool: 20 workers by default (22 physical cores, 44 logical processors;
 bounded by physical cores, one kept free)`  => 上游有意留 1 核；
 默认 aux 落点 `CPUs 22,21,43` 证明 core 21 是给 aux(prefill helper/driver) 的；
 显式 21 后 aux 只剩 `CPUs 22`（与 host 同物理核，help 明说不可），实测 S/M/L 三档 -4.6%/-2.1%/-3.4%。
"""
import io, shutil, time
REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
shutil.copy2(REG, REG + ".bak_w776c1b2_" + time.strftime("%Y%m%d_%H%M%S"))
lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
out, hit = [], False
for ln in lines:
    if ln.startswith("P26\t"):
        f = ln.split("\t")
        f[3] = "CALIBRATED"
        f[5] = "REJECTED"
        f[9] = ("【W776-C1b 2026-10-22 回滚】显式 21 实测三档全降：S 406.5 vs 历史 425.9（-4.6%）、"
                "M 483.8 vs 494.1（-2.1%）、L(99,381 tok) 462.8 vs 479（-3.4%）。"
                "机理（0.1.47 源码/日志）：`CPU pool: 20 workers by default (22 physical cores, 44 logical processors; "
                "**bounded by physical cores, one kept free**)` => 上游有意留 1 个物理核；默认 `aux cpus: ... go to CPUs 22,21,43` "
                "证明 core 21 是 aux(prefill helper / GPU driver) 的落点；显式 21 后 aux 只剩 `CPUs 22`（与 host 同物理核，"
                "help 原文 'never a CPU that shares a core with a worker'）。"
                "**P26 原 calibrate（21=36.0 最优）在 0.1.47 上失效**：那时默认就是 21、没有 'one kept free' 的上限。"
                "=> 维持默认 20（不设 --pool-workers）。")
        f[10] = "回滚：0.1.47 有意留 1 核给 aux；显式 21 实测 -2~-5%"
        ln = "\t".join(f); hit = True
    out.append(ln)
assert hit
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("P26 rolled back to default")
