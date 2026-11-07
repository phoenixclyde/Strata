#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT28: make W832 single-source and navigable; kill line-number pointers."""
import io
import os
import re

ROOT = "D:/workbuddy_space/strata_ws/"
PLAN = ROOT + "deploy/W832_OPT_PLAN_V2.md"


def sub(path, old, new, label, count=1):
    p = ROOT + path
    s = io.open(p, encoding="utf-8").read()
    assert s.count(old) == count, "%s: expected %d, got %d" % (label, count, s.count(old))
    io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, count))
    print("ok", label)


def build_directory():
    lines = io.open(PLAN, encoding="utf-8").read().splitlines()
    heads = []
    for i, l in enumerate(lines):
        if re.match(r"^#{2,3}\s+(?:§6\.5\s+)?回写\s*·\s*W\d+|AUDIT", l):
            # first substantive line after the heading
            body = ""
            for x in lines[i + 1:i + 8]:
                x = x.strip()
                if not x or x.startswith(">"):
                    continue
                body = re.sub(r"[*`|]", "", x)
                body = re.sub(r"\s+", " ", body)
                break
            title = re.sub(r"^#+\s*", "", l).strip()
            title = title.replace("§6.5 ", "")
            heads.append((title, body[:76]))
    out = ["### 6.5.0 回写块目录（AUDIT28 机械生成，别再从 2,300 行里翻）", "",
           "现行队列**只在 §0.1**；下表每一块都是「当时做了什么、结论是什么」的历史记录，",
           "块内出现的 `重排 / 队列第 1 序 / 执行顺序` 一律是**带日期的快照**。", "",
           "| 小节 | 一句结论（取块首非空行） |", "|---|---|"]
    for title, body in heads:
        out.append("| `%s` | %s |" % (title.replace("|", "\\|")[:78], (body or "—").replace("|", "\\|")))
    out += ["", "共 **%d** 块；新增回写块时，`tools/plan_single_source.py` 会要求目录同步。" % len(heads), ""]
    return "\n".join(out) + "\n", len(heads)


def main():
    s = io.open(PLAN, encoding="utf-8").read()

    # --- 0.2 navigation
    nav = """### 0.2 本件怎么读（AUDIT28 · 单源化）

| 要找什么 | 只去这里 | 别处是什么 |
|---|---|---|
| 现在是多少（分母 / 队列 / 生产值 / 2K 相位 / 版本指针） | **§0.1 唯一事实块** | 其余章节的数字必须带轮次与证据件，或明确标成**历史快照** |
| 下一步做哪个 | **§0.1 唯一队列** | §6.5 里所有「重排 / 队列第 1 序 / 执行顺序」都是带日期的历史快照，不是现行排期 |
| 某条目是什么、判据是什么 | `§6.2` / `§6.2.1` 定义表 | §6.5 回写块只记「当时做了什么、结论是什么」 |
| 历轮回写块在哪 | `§6.5.0 回写块目录` | 不要在 2,300 行里逐段翻 |
| 已退役数字 | `附录 A` + `tools/plan_retired.py` | 以现行事实出现即 FAIL |
| 未结项与解除条件 | `deploy/PROGRESS.tsv`（唯一分母） | 本件不另开待办清单 |
| 引用位置 | 写**小节名**（`W832 §6.2 R51`） | 禁写 `W832:<行号>`：每次回写都会让它漂移，`tools/plan_single_source.py` 会拦 |

"""
    anchor = "| 已退役数字 | 见 **附录 A** | `tools/plan_retired.py` 拦「以现行事实出现」 |\n"
    assert s.count(anchor) == 1
    s = s.replace(anchor, anchor + "\n" + nav, 1)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)
    print("ok §0.2 navigation")

    # --- 6.5 general banner + 6.5.0 directory
    head = "### 6.5 队列（**唯一排序处**；条目定义在 §6.2 / §6.2.1，不在这里重复）\n"
    assert s.count(head) == 1
    directory, n = build_directory()
    banner = (
        "\n> **【AUDIT28 · 2026-11-07】本节从这一行起全是历史记录。** "
        "「唯一排序处」是 2026-10-31 的旧说法：**现行队列只在 §0.1**，见 §0.2 导航。"
        "下面所有 `重排（日期）/ 队列第 1 序 / 执行顺序 / 队列首位` 都是当时的快照，"
        "不因写在后面就更权威；`tools/plan_single_source.py` 逐行校验。\n\n")
    s = io.open(PLAN, encoding="utf-8").read()
    s = s.replace(head, head + banner + directory, 1)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)
    print("ok §6.5 banner + directory (%d blocks)" % n)

    # --- stale "current" pointer + plain historical statements
    sub("deploy/W832_OPT_PLAN_V2.md",
        "**现行（2026-11-01 起，AUDIT16 后）**：上面四条是历史沿革；**当前按 §6.5 顶部的四条权重排序**",
        "**【AUDIT28 更正】现行排期只认 §0.1 唯一队列**；上面四条与本节所有权重/重排文字"
        "都是 2026-11-01 起的**历史快照**，§6.5 顶部也不再是排序处",
        "line 95")

    sub("deploy/W832_OPT_PLAN_V2.md",
        "而 W1003 的结论**直接改写队列第 1 序（R97）与第 3 序（R86）**——这正是本节存在的意义，我却跳过了。",
        "而 W1003 的结论**直接改写队列第 1 序（R97）与第 3 序（R86）**（历史快照，2026-11-05）——"
        "这正是本节存在的意义，我却跳过了。",
        "line 1056")

    sub("deploy/W832_OPT_PLAN_V2.md",
        "机主令「继续」。队列首位是 R95，而 W1015 刚把 91 ms 的机制写成「复用等待（双缓冲可解）」。",
        "机主令「继续」。队列首位是 R95（历史快照，2026-11-05），而 W1015 刚把 91 ms 的机制写成「复用等待（双缓冲可解）」。",
        "line 1562")

    # --- replace W832:<line> pointers in ACTIVE docs with stable section names
    mapping = {
        24: "§0.1 进度分母", 26: "§0.1 ROCm", 28: "§0.1 唯一队列",
        48: "§0 收口说明", 139: "§4.1", 158: "§4.2", 226: "§4.3",
        236: "§4.4", 264: "§4.5", 470: "§6.2", 529: "§6.2 R101",
        530: "§6.2 R102", 803: "§6.2 新表", 1404: "§6.5 报告门", 2055: "§6.6",
    }
    active = []
    for f in sorted(os.listdir(ROOT + "deploy")):
        if not f.endswith((".md", ".tsv")):
            continue
        if f.startswith("AUDIT") or f in ("PROGRESS.tsv", "W832_OPT_PLAN_V2.md", "SESSION_STATE.md"):
            if f == "AUDIT_LEDGER.tsv":
                continue           # frozen historical evidence locators, see AUDIT28 §1
            active.append("deploy/" + f)
    active += ["tools/plan_lint.py", "albus/w1031/reply.md", "albus/w1032/reply.md"]
    nref = 0
    for p in active:
        fp = ROOT + p
        t = io.open(fp, encoding="utf-8", errors="replace").read()
        if not re.search(r"W832:\d+", t):
            continue
        def rp(m):
            global nref
            nref += 1
            return "W832 " + mapping.get(int(m.group(1)), "§0.1")
        io.open(fp, "w", encoding="utf-8", newline="\n").write(re.sub(r"W832:(\d+)", rp, t))
    print("ok line-number pointers replaced:", nref)


if __name__ == "__main__":
    main()
