# -*- coding: utf-8 -*-
"""W953 remediation: retract the two wrong claims about version ordering / get_J_max."""
import io

D = "D:/workbuddy_space/strata_ws/deploy/"


def rep(name, old, new):
    p = D + name
    s = io.open(p, encoding="utf-8").read()
    if new[:30] in s:
        return name + " already"
    if old not in s:
        return name + " MISS"
    io.open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))
    return name + " ok"


OLD948 = """**\u3010AUDIT24 P1 \u00b7 2026-11-04\u3011\u7248\u672c\u5e8f\u7684\u5224\u636e\u65e0\u6548**"""
# build the long literals from a file-free approach: use explicit pieces to avoid quote clashes
old948 = (
    "> **【AUDIT24 P1 · 2026-11-04】版本序的判据无效**：`get_J_max` 在**上游 master 也是 0**\n"
    "> （本地 `mmq_upstream.cuh` 79,586 B，`grep -c get_J_max` = 0；只有我们 pin 的 `mmq.cuh` 有 1 处）\n"
    "> ⇒ 它是**我们自己的补丁**，不能当\uff02谁更新\uff02的标志；`3cf03257` 也只出现在 `bench/results/*/README.md`\n"
).replace("\uff02", '"')
# the tail of the original banner is matched loosely: cut at the sentence we know verbatim
p948 = D + "W948_REPORT_LINT_AND_LLAMA_VERSION.md"
s = io.open(p948, encoding="utf-8").read()
if "【W953 更正" in s:
    print("W948 already")
else:
    i = s.find("> **【AUDIT24 P1 · 2026-11-04】版本序的判据无效**")
    j = s.find("再谈\"换基线\"。", i)
    if i < 0 or j < 0:
        print("W948 MISS", i, j)
    else:
        j = s.find("\n", j)
        new = (
            "> **【W953 更正 · 2026-11-04】本件（及其 AUDIT24 横幅）的版本判断作废，方向反了。**\n"
            "> 正确锚点：我们的 `llama.cpp/CMakeLists.txt` 写着 **LLAMA_VERSION 0.4.1**，且\n"
            "> `ggml/src/ggml-cuda/mmq.cuh` 与 upstream **`e6ab7c1a4` 逐字节相同（diff = 0，71,851 B）**\n"
            "> ⇒ 我们就是 **0.4.1（2026-09-22）**。\n"
            "> 同字段各 tag：`e6ab7c1a4` 0.4.1 · `b11553`(mx) **0.6.0** · exabit **0.7.0** · `b12099`/master **0.8.0**。\n"
            "> ⇒ **「三家 fork 都比我们旧」是错的**：mx / exabit 都比我们新，只有 furnace 与我们同基座。\n"
            "> `get_J_max` 是 **0.4.1 时代的上游符号、后被上游删除**（furnace 同基座但重写了 MMQ）——\n"
            "> 所以「有它 = 更旧」，不是「我们的补丁」。`R90` 因此**从方向成立升级为硬事实：落后 4 个 minor**。"
        )
        s = s[:i] + new + s[j:]
        io.open(p948, "w", encoding="utf-8", newline="").write(s)
        print("W948 ok")

# W946: append one line after the "见 R90。" of the banner
p946 = D + "W946_GFX906_PROJECTS_LANDSCAPE.md"
s = io.open(p946, encoding="utf-8").read()
if "【W953 更正】" in s:
    print("W946 already")
elif "> 见 `R90`。\n" in s:
    add = (
        "> 见 `R90`。**【W953 更正】**版本号是**可用**的锚点（`LLAMA_VERSION` 就在我们自己 CMakeLists 里）：\n"
        "> 本件当时写的「社区 v0.7.0」在今天是 **0.8.0**（`b12099`），我们仍是 **0.4.1** ⇒ 差 4 个 minor。\n"
        "> 上一轮 `W948` 说「版本号不可比」、`AUDIT24` 跟着写「get_J_max 是自家补丁」，两条都已作废，见 `W953`。\n"
    )
    io.open(p946, "w", encoding="utf-8", newline="").write(s.replace("> 见 `R90`。\n", add, 1))
    print("W946 ok")
else:
    print("W946 MISS")

# W832: replace the two-line correction
p832 = D + "W832_OPT_PLAN_V2.md"
s = io.open(p832, encoding="utf-8").read()
if "【W953 更正】版本号是可比的" in s:
    print("W832 already")
else:
    old = (
        "> **【AUDIT24 更正】版本号不是可比锚点**（`W948` 自查）：`get_J_max` 在上游 master 也是 0 ⇒ 那是我们自己的补丁；\n"
        "> `3cf03257` 只出现在别人的 bench README。能确认的只有**我们与上游 master 差 587 行**；`R90` 保留，但 S1 先做 pin→tag 映射。"
    )
    new = (
        "> **【W953 更正】版本号是可比的，而且已经钉死**：我们的 `CMakeLists.txt` 写 **LLAMA_VERSION 0.4.1**，\n"
        "> 且 `mmq.cuh` 与 upstream **`e6ab7c1a4` 逐字节相同（diff 0）** ⇒ 我们 = **0.4.1（2026-09-22）**。\n"
        "> 同字段：mx(`b11553`) **0.6.0** · exabit **0.7.0** · 上游 `b12099`/master **0.8.0** ⇒ **落后 4 个 minor**。\n"
        "> 「三家 fork 更旧」作废（mx/exabit 比我们新，furnace 同基座）；`get_J_max` 是 0.4.1 的上游符号、后被删。\n"
        "> ⇒ **`R90` 升为队列第一位**（`W954`）。"
    )
    if old in s:
        io.open(p832, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))
        print("W832 ok")
    else:
        print("W832 MISS")
