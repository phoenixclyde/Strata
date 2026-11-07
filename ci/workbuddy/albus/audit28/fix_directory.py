#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate the §6.5.0 directory so it covers EVERY 回写 block (incl. non-W ones)."""
import io
import re

P = "D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md"


def main():
    s = io.open(P, encoding="utf-8").read()
    L = s.splitlines()
    start = next(i for i, l in enumerate(L) if l.startswith("### 6.5.0 回写块目录"))
    end = next(i for i in range(start + 1, len(L)) if L[i].startswith("> **【AUDIT27 更正"))
    heads = []
    for i, l in enumerate(L):
        if i <= start:
            continue
        m = re.match(r"^#{2,3}\s+(?:§6\.5\s+)?(回写\s*·\s*.+)$", l)
        if not m:
            continue
        body = ""
        for x in L[i + 1:i + 8]:
            x = x.strip()
            if not x or x.startswith(">") or x.startswith("|"):
                continue
            x = re.sub(r"^#+\s*", "", x)
            body = re.sub(r"\s+", " ", re.sub(r"[*`]", "", x))
            break
        heads.append((m.group(1).strip(), body[:76]))
    out = ["### 6.5.0 回写块目录（AUDIT28 机械生成，别再从 2,300 行里翻）", "",
           "现行队列**只在 §0.1**；下表每一块都是「当时做了什么、结论是什么」的历史记录，",
           "块内出现的 `重排 / 队列第 1 序 / 执行顺序` 一律是**带日期的快照**。", "",
           "| 小节 | 一句结论（取块首非空行） |", "|---|---|"]
    for title, body in heads:
        out.append("| `%s` | %s |" % (title.replace("|", "\\|")[:78], (body or "—").replace("|", "\\|")))
    out += ["", "共 **%d** 块（含 `回写 · AUDIT27` 这类非 W 编号块）；新增回写块时，"
            "`tools/plan_single_source.py` 会要求目录同步。" % len(heads), "", ""]
    L[start:end] = out
    io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print("directory rebuilt with", len(heads), "blocks")


if __name__ == "__main__":
    main()
