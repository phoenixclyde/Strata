#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT28 -- W832 must have exactly one live queue and no rot-prone pointers.

W1007 deleted one duplicate execution-order table; 67 more rounds of §6.5 回写
brought back 20 self-held "队列" lines and 10 dated re-order snapshots.  A reader
could pick any of them as current.  This gate enforces:
  1 exactly one `| **唯一队列** |` row, inside §0.1
  2 §0.2 navigation + §6.5.0 directory exist, and the directory names every 回写 block
  3 historical ordering declarations are blockquotes or explicitly marked snapshots
  4 no `W832:<line>` pointer in active docs (use section names instead)
  5 §0.1 denominator equals PROGRESS.tsv (see also tools/audit_scope.py §D)

  python tools/plan_single_source.py [--self-test]
"""
import io
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
PROG = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
ORDER = re.compile(r"队列第\s*1\s*序|队列改为|升为队列第一位|插到最前|唯一执行序|"
                   r"队列首位是|本行即执行顺序|当前按 §6\.5|执行顺序（20|队列仍以本节")
HIST = re.compile(r"历史快照|已撤回|已并入|AUDIT2[78]|~~|SUPERSEDED|已结|作废")


def active_docs():
    out = []
    for f in sorted(os.listdir(os.path.join(ROOT, "deploy"))):
        if f == "AUDIT_LEDGER.tsv":
            continue           # frozen evidence locators, documented in AUDIT28 §1
        if f.endswith((".md", ".tsv")) and (f.startswith("AUDIT") or f in
                                           ("PROGRESS.tsv", "W832_OPT_PLAN_V2.md", "SESSION_STATE.md")):
            out.append(os.path.join(ROOT, "deploy", f))
    for f in ("plan_lint.py", "plan_retired.py", "audit_index.py", "audit_outputs.py"):
        out.append(os.path.join(ROOT, "tools", f))
    for p in ("albus/w1031/reply.md", "albus/w1032/reply.md", "albus/w1033/reply.md",
              "albus/w1034/reply.md"):
        out.append(os.path.join(ROOT, p))
    return [p for p in out if os.path.isfile(p)]


def check(quiet=False):
    text = io.open(PLAN, encoding="utf-8").read()
    L = text.splitlines()
    fails = []
    # 1 single queue
    q = [i for i, l in enumerate(L) if l.startswith("| **唯一队列** |")]
    sec02 = next((i for i, l in enumerate(L) if l.startswith("### 0.2")), len(L))
    if len(q) != 1 or q[0] > sec02:
        fails.append("1: expected exactly one §0.1 唯一队列 row, got %d" % len(q))
    # 2 navigation + directory coverage
    if "### 0.2 本件怎么读" not in text:
        fails.append("2: §0.2 navigation missing")
    d0 = next((i for i, l in enumerate(L) if l.startswith("### 6.5.0 回写块目录")), -1)
    if d0 < 0:
        fails.append("2: §6.5.0 directory missing")
    else:
        d1 = next((i for i in range(d0 + 1, len(L)) if L[i].startswith("> **【AUDIT27 更正")), len(L))
        rows = "\n".join(L[d0:d1])
        heads = [re.sub(r"^#+\s*(?:§6\.5\s+)?", "", l).strip()
                 for l in L if re.match(r"^#{2,3}\s+(?:§6\.5\s+)?回写\s*·", l)]
        miss = [h for h in heads if h[:24] not in rows]
        if miss:
            fails.append("2: directory misses %d 回写 blocks: %s" % (len(miss), miss[:2]))
    # 3 ordering declarations are historical
    plain = [(i + 1, l.strip()[:90]) for i, l in enumerate(L)
             if ORDER.search(l) and not l.lstrip().startswith(">") and not HIST.search(l)]
    if plain:
        fails.append("3: %d ordering lines read as current: %s" % (len(plain), plain[:2]))
    # 4 line-number pointers
    rot = []
    for p in active_docs():
        for i, l in enumerate(io.open(p, encoding="utf-8", errors="replace"), 1):
            if re.search(r"W832:\d+", l):
                rot.append("%s:%d" % (os.path.basename(p), i))
    if rot:
        fails.append("4: line-number pointers rot on every edit: %s" % rot[:4])
    # 5 denominator
    tot = done = 0
    for l in io.open(PROG, encoding="utf-8"):
        f = l.rstrip("\n").split("\t")
        if len(f) >= 10 and f[0] != "block" and not l.startswith("#"):
            try:
                tot += int(f[5]); done += int(f[6])
            except ValueError:
                pass
    m = re.search(r"\| 进度分母 \| \*\*(\d+) 条 / 已结 (\d+) / ([\d.]+)%\*\*", text)
    if not m or (int(m.group(1)), int(m.group(2))) != (tot, done):
        fails.append("5: §0.1 denominator != PROGRESS.tsv %d/%d" % (tot, done))
    if not quiet:
        print("PLAN_SINGLE_SOURCE: queue_rows=%d 回写_blocks=%d ordering_lines=%d rot_ptr=%d denom=%d/%d" %
              (len(q), len(heads) if d0 >= 0 else 0,
               sum(1 for l in L if ORDER.search(l)), len(rot), tot, done))
        if fails:
            print("PLAN_SINGLE_SOURCE: FAIL (%d)" % len(fails))
            for f in fails:
                print("   " + f)
        else:
            print("PLAN_SINGLE_SOURCE: PASS (one queue, navigable, no rot-prone pointers)")
    return fails


def self_test():
    ok = 0
    L = io.open(PLAN, encoding="utf-8").read().splitlines()
    ok += 1 if len([l for l in L if l.startswith("| **唯一队列** |")]) == 1 else 0
    bad = "队列首位是 R95，而 W1015 刚把 91 ms 的机制写成复用等待"
    ok += 1 if ORDER.search(bad) and not HIST.search(bad) else 0
    good = "队列首位是 R95（历史快照，2026-11-05）"
    ok += 1 if HIST.search(good) else 0
    ok += 1 if re.search(r"W832:\d+", "see W832:123") else 0
    print("SELF_TEST: %d/4" % ok)
    return 0 if ok == 4 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(1 if check() else 0)
