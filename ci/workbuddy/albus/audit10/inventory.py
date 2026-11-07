#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT10 盘点：把 W801-W809 每个驱动文件的「臂 / 行类型 / 中止点」列出来。
   不看我自己写的文档，只看原始件。
"""
import glob
import os
import re
import sys

D = "albus/audit10"
KIND = [
    ("ARM", re.compile(r"^=== ARM\s+(\S+)")),
    ("CFGCHECK", re.compile(r"^\s+CFGCHECK")),
    ("ENVCHECK", re.compile(r"^\s+ENVCHECK")),
    ("FUSECHECK", re.compile(r"^\s+FUSECHECK")),
    ("VW", re.compile(r"^\s+VW ")),
    ("BINCHECK", re.compile(r"^\s+BINCHECK")),
    ("DT", re.compile(r"^\s+DT strata decode timing")),
    ("PH", re.compile(r"^\s+PH strata")),
    ("SV", re.compile(r"^\s+SV strata")),
    ("MEDIAN", re.compile(r"^\s+MEDIAN")),
    ("OKN", re.compile(r"^\s+OKN")),
    ("POOL", re.compile(r"^\s+POOL")),
    ("SCORE", re.compile(r"^\s+SCORE")),
    ("PARITY", re.compile(r"^\s+PARITY")),
    ("CHUNK", re.compile(r"^\s+CHUNK")),
    ("LOGPOS", re.compile(r"^\s+LOGPOS")),
    ("ABORT", re.compile(r"ABORT|!! ")),
    ("DONE", re.compile(r"^== DONE")),
    ("RESTORED", re.compile(r"^\s*restored |trap-restored")),
    ("TURN", re.compile(r"^T\d+ ")),
    ("ROW", re.compile(r"^\s+(46|79|108|237|277|529|547|1008|1909|1954)\s")),
]


def scan(path):
    arms, counts, order = {}, {}, []
    cur = None
    abort = []
    for ln in open(path, encoding="utf-8", errors="replace"):
        hit = False
        for name, rx in KIND:
            if rx.search(ln):
                counts[name] = counts.get(name, 0) + 1
                if name == "ARM":
                    cur = rx.search(ln).group(1)
                    if cur not in arms:
                        arms[cur] = 0
                        order.append(cur)
                    arms[cur] += 1
                if name == "ABORT":
                    abort.append(ln.strip()[:80])
                hit = True
                break
        if not hit and cur:
            pass
    return order, arms, counts, abort


def main():
    files = sorted(glob.glob(os.path.join(D, "w80*.txt")))
    print("%-42s %-6s %-22s %s" % ("file", "bytes", "arms(×blocks)", "line kinds"))
    for f in files:
        n = os.path.getsize(f)
        if n == 0:
            print("%-42s %-6d (empty)" % (os.path.basename(f), n))
            continue
        order, arms, counts, abort = scan(f)
        kinds = ",".join("%s=%d" % (k, v) for k, v in sorted(counts.items()) if k != "ARM")
        armstr = ",".join("%s×%d" % (a, arms[a]) for a in order) if order else "-"
        print("%-42s %-6d %-22s %s" % (os.path.basename(f), n, armstr[:22], kinds[:150]))
        if abort:
            print("     ABORT: " + " | ".join(abort[:2]))


if __name__ == "__main__":
    main()
