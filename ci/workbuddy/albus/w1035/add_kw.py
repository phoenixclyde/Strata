"""给 W1035 的账本行补第 11 列 `KW:`（检索键），并让脚本自己挑掉不合格的词。

规则与 claim_homes.py 完全一致：词长>=3、全账本命中<=25 行、且必须出现在本行文本里。
不合格的候选直接丢弃；一行的候选全废就报出来（说明这行根本没按该说法写下结论）。
"""
import io
import os
import shutil

PROG = "deploy/PROGRESS.tsv"
MIN_TERM = 3
GENERIC_LIMIT = 25

CAND = {
    "P407": ["静态重估", "tile", "q8_bytes", "J_best", "2304"],
    "P408": ["mmap 缺页", "shard-2", "驻留", "页不会过期", "13.9"],
    "P410": ["拉式", "fail-open", "ensure_ascii", "四件套", "Stop 钩子"],
    "P411": ["dispatch", "round_gate", "Actions 未禁用", "204"],
    "P412": ["分支保护", "Stop 钩子", "Bypassed", "直推"],
    "P413": ["deploy_gate", "PR-only", "判据输出", "D1–D6"],
    "P414": ["3.5/8", "九个阀门", "证据门", "gh_gate"],
    "P415": ["独立技能", "quick_validate", "不建", "热加载"],
    "P416": ["decode 不稳", "corr 0.49", "命中率", "误命中"],
}


def main():
    lines = io.open(PROG, encoding="utf-8").read().splitlines()
    all_text = ["\t".join(l.split("\t")) for l in lines]
    rows = {l.split("\t")[1]: i for i, l in enumerate(lines) if l.count("\t") >= 8}

    changed, problems = [], []
    for pid, cands in CAND.items():
        i = rows.get(pid)
        if i is None:
            problems.append("%s 不在账本里" % pid)
            continue
        f = lines[i].split("\t")
        body = " ".join(f[2:3] + f[8:])
        ok = []
        for t in cands:
            if len(t) < MIN_TERM:
                continue
            spread = sum(1 for g in all_text if t in g)
            if spread > GENERIC_LIMIT:
                continue
            if t not in body:
                continue
            ok.append(t)
        if len(ok) < 2:
            problems.append("%s 只找到 %d 个合格检索词 %s（候选=%s）" % (pid, len(ok), ok, cands))
            continue
        while len(f) < 11:
            f.append("")
        f[10] = "KW:" + "|".join(ok[:3])
        lines[i] = "\t".join(f)
        changed.append("%s -> %s" % (pid, f[10]))

    if changed:
        shutil.copyfile(PROG, PROG + ".bak_w1035k")
        io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for c in changed:
        print("  " + c)
    for p in problems:
        print("  !! " + p)
    print("changed=%d problems=%d" % (len(changed), len(problems)))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
