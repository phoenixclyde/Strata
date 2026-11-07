#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inventory: (a) every ledger id minted this round, (b) every rule currently enforced.

只从文件里读，不靠记忆：
  PROGRESS.tsv  source == 本轮
  albus/w1034/HANDOFF.md §5 的 1..N 条铁律
  albus/w1002/round_close.py 的 HARD / SCRIPT_HARD / SOFT
  ~/.workbuddy/settings.json 的 hooks
  ci/ 下的门脚本
"""
import io
import json
import os
import re
import sys

ROOT = "D:/workbuddy_space/strata_ws"
ROUND = "W1035"
PROG = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
HANDOFF = os.path.join(ROOT, "albus", "w1034", "HANDOFF.md")
RC = os.path.join(ROOT, "albus", "w1002", "round_close.py")
SETTINGS = os.path.expanduser("~/.workbuddy/settings.json")


def rows(round_id):
    out = []
    for l in io.open(PROG, encoding="utf-8", errors="replace").read().splitlines():
        f = l.split("\t")
        if len(f) >= 9 and f[3:4] == [round_id]:
            out.append((f[0], f[1], f[2], f[6], f[7]))
    return out


def handoff_rules():
    txt = io.open(HANDOFF, encoding="utf-8", errors="replace").read()
    s = txt[txt.find("## 5 铁律全表"):txt.find("## 6 门清单")]
    cur, out = "", []
    for line in s.splitlines():
        m = re.match(r"^\*\*([A-E])\. (.+?)\*\*$", line.strip())
        if m:
            cur = m.group(1) + " " + m.group(2)
            continue
        m = re.match(r"^(\d+)\.\s+(.+)$", line.strip())
        if m:
            out.append((cur[:4], int(m.group(1)), m.group(2)[:96]))
    return out


def gates():
    txt = io.open(RC, encoding="utf-8", errors="replace").read()
    hard = re.search(r"HARD\s*=\s*\[(.*?)\]", txt, re.S).group(1)
    hard = re.findall(r'"([^"]+\.py)"', hard)
    script = re.findall(r'\(\s*ROOT / "([^"]+)"', txt)
    soft = re.search(r"SOFT\s*=\s*\[(.*?)\]", txt, re.S).group(1)
    soft = re.findall(r'"([^"]+\.py)"', soft)
    return hard, script, soft


def hooks():
    d = json.loads(io.open(SETTINGS, encoding="utf-8").read())
    out = []
    for ev, arr in (d.get("hooks") or {}).items():
        for a in arr:
            for h in a.get("hooks", []):
                out.append((ev, a.get("matcher", "") or "*", os.path.basename(h.get("command", "").split()[-1].strip('"'))))
    return out


def main():
    print("== A. 本轮（%s）新开编号 ==" % ROUND)
    for block, pid, item, done, status in rows(ROUND):
        print("  %-6s %-24s done=%s %-6s %s" % (pid, block, done, status, item[:70]))
    print("  （另有 1 处只改备注、未开新号：P265）")

    print("\n== B. 铁律（HANDOFF §5）==")
    r = handoff_rules()
    print("  共 %d 条" % len(r))
    for g, n, t in r:
        print("  %-4s %2d. %s" % (g, n, t))

    print("\n== C. 收工门（round_close.py）==")
    hard, script, soft = gates()
    print("  HARD %d：%s" % (len(hard), " · ".join(x[:-3] for x in hard)))
    print("  SCRIPT_HARD %d：%s" % (len(script), " · ".join(os.path.basename(x) for x in script)))
    print("  SOFT %d：%s" % (len(soft), " · ".join(x[:-3] for x in soft)))

    print("\n== D. 钩子（settings.json）==")
    for ev, matcher, f in hooks():
        print("  %-14s matcher=%-22s -> %s" % (ev, matcher, f))
    return 0


if __name__ == "__main__":
    sys.exit(main())
