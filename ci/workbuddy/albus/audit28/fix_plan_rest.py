#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""remaining plan fixes (first half of fix_plan.py already applied)."""
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


def main():
    old_q = "机主令「继续」。队列首位是 R95，而 W1015 刚把 91 ms 的机制写成「复用等待（双缓冲可解）」。"
    if old_q in io.open(PLAN, encoding="utf-8").read():
        sub("deploy/W832_OPT_PLAN_V2.md",
            old_q,
            "机主令「继续」。队列首位是 R95（历史快照，2026-11-05），而 W1015 刚把 91 ms 的机制写成「复用等待（双缓冲可解）」。",
            "queue snapshot line", count=2)
    else:
        print("skip queue snapshot line (already applied)")

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
                continue
            active.append("deploy/" + f)
    active += ["tools/plan_lint.py", "albus/w1031/reply.md", "albus/w1032/reply.md"]
    nref = 0
    for p in active:
        fp = ROOT + p
        t = io.open(fp, encoding="utf-8", errors="replace").read()
        if not re.search(r"W832:\d+", t):
            continue
        def rp(m):
            nonlocal nref
            nref += 1
            return "W832 " + mapping.get(int(m.group(1)), "§0.1")
        io.open(fp, "w", encoding="utf-8", newline="\n").write(re.sub(r"W832:(\d+)", rp, t))
    print("ok line-number pointers replaced:", nref)


if __name__ == "__main__":
    main()
