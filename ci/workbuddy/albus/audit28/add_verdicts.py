#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT28: give every numbered AUDIT artefact one machine-readable verdict line.

The index's P columns used to be hand-copied (AUDIT26 F1, W1007).  AUDIT27 made
the *sum* derived, but the per-row numbers were still unverifiable against the
artefact.  This writes a single canonical line into each artefact; tools/audit_outputs.py
then fails if the index row ever drifts from it.
"""
import io
import os
import re

ROOT = "D:/workbuddy_space/strata_ws/"
IDX = ROOT + "deploy/AUDIT_INDEX.md"

NO_FORMAL_VERDICT = {
    15: "方案本体审计；原件无 P 计数小节，9 条 P1 见 §6/§7 逐条结论",
    18: "单轮审计；原件只有级别定义，3/3/2 见正文逐条判定",
    19: "整改类（非 P 分级），索引四列为 — ⇒ 机读按 0 计",
    20: "原件只有级别定义，2/10/5 见正文发现表",
    21: "原件只有级别定义，4/7/5 见正文发现表",
    22: "整改类；2/1/1 见 §P0-A/§P0-B 与 P1/P2 小节",
    25: "六轴全面审计；2/7/6 见 §1 严重度总览",
    26: "0/3/2 见 §2 结论表；另两条「上游数字错」中 #31188 那条已由 AUDIT28 撤回",
}


def index_rows():
    out = {}
    for line in io.open(IDX, encoding="utf-8"):
        m = re.match(r"\|\s*\**\s*AUDIT(\d+)\s*\**\s*\|", line)
        if not m:
            continue
        cells = [c.strip().strip("*").strip() for c in line.strip().strip("|").split("|")]
        nums = [int(c) if re.fullmatch(r"\d+", c) else 0 for c in cells[2:6]]
        f = cells[6].strip().strip("`") if len(cells) > 6 else ""
        out[int(m.group(1))] = (nums, f)
    return out


def main():
    rows = index_rows()
    done = []
    for n, (nums, fname) in sorted(rows.items()):
        p = ROOT + "deploy/" + fname
        assert os.path.isfile(p), "missing artefact " + fname
        s = io.open(p, encoding="utf-8").read()
        if re.search(r"^> VERDICT: AUDIT%d\b" % n, s, re.M):
            print("skip (already has VERDICT)", fname)
            continue
        lines = s.splitlines(keepends=True)
        assert lines and lines[0].lstrip().startswith("#"), "no title line: " + fname
        a, b, c, d = nums
        ins = ("> VERDICT: AUDIT%d P0=%d P1=%d P2=%d P3=%d src=AUDIT_INDEX:%d"
               "（AUDIT28 回填，不新增结论）\n" % (n, a, b, c, d, n))
        if n in NO_FORMAL_VERDICT:
            ins += ("> **总判补录（AUDIT28）**：本件原无统一「总判」小节；"
                    + NO_FORMAL_VERDICT[n]
                    + "。此处只把已存在的分级写成机读行，**不改写任何结论**。\n")
        ins += "\n"
        io.open(p, "w", encoding="utf-8", newline="\n").write(lines[0] + "\n" + ins + "".join(lines[1:]))
        done.append("AUDIT%d=%s" % (n, "/".join(map(str, nums))))
    print("inserted", len(done), "verdict lines")
    print(" ".join(done))


if __name__ == "__main__":
    main()
