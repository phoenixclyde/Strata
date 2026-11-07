#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT28: add the AUDIT28 row, the COMPANIONS inventory and the ledger loc policy."""
import io
import os
import re

ROOT = "D:/workbuddy_space/strata_ws/"
IDX = ROOT + "deploy/AUDIT_INDEX.md"
DEP = ROOT + "deploy"


def main():
    s = io.open(IDX, encoding="utf-8").read()
    assert s.count("| **合计** |") == 1
    row = ("| **AUDIT28** | **整改类：22 件编号审计 + 39 件派生产物 + 2 本台账 + 方案本体**；"
           "1 P0（AUDIT26 对 #31188 的「PR 内无性能栏」误判，已全链撤回）、4 P1（机读总判 / 派生产物清单 / "
           "方案单源化 / 行号指针）、3 P2（外网补核 / 退役理由 / 冻结件纪律）；**外网复核 5 组** | "
           "**1** | **4** | **3** | **0** | `AUDIT28_OUTPUT_REMEDIATION.md` |\n")
    assert "AUDIT28_OUTPUT_REMEDIATION.md" not in s
    s = s.replace("| **合计** |", row + "| **合计** |", 1)

    # companion inventory (all audit-ish .md that are not a numbered index artefact)
    numbered = set()
    for line in s.splitlines():
        m = re.match(r"\|\s*\**\s*AUDIT(\d+)\s*\**\s*\|", line)
        if m:
            c = [x.strip().strip("*").strip() for x in line.strip().strip("|").split("|")]
            if len(c) > 6:
                numbered.add(c[6].strip().strip("`"))
    comp = sorted(f for f in os.listdir(DEP)
                  if f.endswith(".md") and f != "AUDIT_INDEX.md" and f not in numbered
                  and re.search(r"AUDIT|VERDICT|REVIEW", f, re.I))
    assert len(comp) == 39, len(comp)
    inv = ("\n## 审计派生产物清单（AUDIT28，机器可验）\n\n"
           "> 39 件 `W*_AUDIT / W*VERDICT / W*REVIEW` 与 `AUDIT17_CLOSURE.md` 是**冻结的历史证据**，"
           "逐字保留、不参与整改；但必须被点名，否则「所有审计输出」永远无法回答有多少件。"
           "`tools/audit_index.py` 的 `want[n]` 对同号文件只留最后一个，配套件原本会被静默覆盖。\n\n"
           "COMPANIONS: " + " ".join(comp) + "\n\n"
           "| 类别 | 数量 | 门的判据 |\n|---|---:|---|\n"
           "| 编号审计件 | %d | 每件一条 `VERDICT:` 且等于索引 P 列 |\n"
           "| 配套/冻结件 | %d | 必须出现在 `COMPANIONS:` 行，文件必须存在 |\n"
           "| 结案台账 | 2 | id 唯一、状态枚举合法、撤回标记仍在 |\n\n" % (len(numbered), len(comp)))
    # append the inventory before the 台账 section
    anchor = "## 台账\n"
    assert s.count(anchor) == 1
    s = s.replace(anchor, inv + anchor, 1)

    # ledger loc policy
    old = ("- `AUDIT_LEDGER.tsv` —— AUDIT12 的 26 条结论逐条登记（id / 严重度 / 位置 / 问题 / 处置 / 状态），\n"
           "  由报告表格**解析生成**，改报告后重跑脚本即可同步，不手抄。")
    if old in s:
        s = s.replace(old, old +
            "\n  **【AUDIT28 口径】** `loc` 列里的 `W828:<行号>` / `W832:<行号>` 是 **2026-10-31 的证据定位快照**，"
            "不是可跟随的现行指针；历史台账不重写，现行位置一律按 `W832 §0.2` 导航读小节名。", 1)

    io.open(IDX, "w", encoding="utf-8", newline="\n").write(s)
    print("index: AUDIT28 row + %d companions + loc policy" % len(comp))
    print(" ".join(comp[:6]), "...")


if __name__ == "__main__":
    main()
