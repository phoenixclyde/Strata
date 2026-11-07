#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1006: audit every round that no audit has covered yet.

The question is not "is the plan pretty" -- it is "does every round that reached a decision
have a ledger row, a plan landing point, and numbers that agree with both".  Earlier audits
covered slices (AUDIT19: W864-W875; W1004: a spot check of 11-04/11-05), so the set of rounds
that no audit has ever looked at is knowable: all rounds minus the audited ranges.

Sources of truth:
  .workbuddy/memory/2026-*.md   round headings -> the round exists, its title, its date
  deploy/PROGRESS.tsv           column `source` -> ledger rows naming the round
  deploy/W832_OPT_PLAN_V2.md    round id mentioned -> plan landing point

Output: one row per round with has_ledger / n_rows / in_plan / statuses, plus a list of gaps.
"""
import io
import os
import re
import sys
from collections import defaultdict

W = r"D:/workbuddy_space/strata_ws"
MEM = os.path.join(W, ".workbuddy/memory")
PLAN = os.path.join(W, "deploy/W832_OPT_PLAN_V2.md")
PROG = os.path.join(W, "deploy/PROGRESS.tsv")

# Ranges an audit has already covered (from the logs).  Anything inside is out of scope.
AUDITED = [
    ("W864", "W875", "AUDIT19 2026-11-02"),
    ("W767", "W775", "W775_AUDIT 2026-10-11"),
    ("W875", "W885", "W1004 邻域补审 2026-11-05"),
]
# The plan itself starts at W832; earlier rounds belong to a previous plan file.
ERA_START = 800

HEAD = re.compile(r"^##\s+(.*)$")


def rounds():
    out = {}
    for f in sorted(os.listdir(MEM)):
        if not f.startswith("2026-") or not f.endswith(".md"):
            continue
        date = f[:-3]
        for line in io.open(os.path.join(MEM, f), encoding="utf-8", errors="replace"):
            m = HEAD.match(line)
            if not m:
                continue
            for wid in re.findall(r"\bW(\d{3})[a-z]?\b", m.group(1)):
                n = int(wid)
                if n < ERA_START:
                    continue
                key = "W%d" % n
                # first heading wins: it carries the round's own title
                if key not in out:
                    out[key] = {"date": date, "title": m.group(1).strip()[:90]}
    return out


def ledger():
    rows = [l.rstrip("\n").split("\t") for l in io.open(PROG, encoding="utf-8")
            if l.strip() and not l.startswith("#")]
    h = rows[0]
    si, ii, st = h.index("source"), h.index("id"), h.index("status")
    per = defaultdict(lambda: {"n": 0, "ids": [], "st": set()})
    for r in rows[1:]:
        if len(r) <= max(si, ii, st):
            continue
        src = r[si]
        for wid in re.findall(r"\bW(\d{3})[a-z]?\b", src):
            key = "W%d" % int(wid)
            per[key]["n"] += 1
            per[key]["ids"].append(r[ii])
            per[key]["st"].add(r[st])
    return per


def plan_text():
    return io.open(PLAN, encoding="utf-8").read()


def audited(key):
    n = int(key[1:])
    for a, b, why in AUDITED:
        if int(a[1:]) <= n <= int(b[1:]):
            return why
    return None


def main():
    R, L, P = rounds(), ledger(), plan_text()
    keys = sorted(R, key=lambda k: int(k[1:]))
    rows = []
    for k in keys:
        in_plan = len(re.findall(r"\b%s\b" % k, P))
        l = L.get(k)
        rows.append({
            "id": k, "date": R[k]["date"], "title": R[k]["title"],
            "n_rows": l["n"] if l else 0,
            "ids": ",".join(l["ids"][:4]) if l else "",
            "st": "/".join(sorted(l["st"])) if l else "-",
            "in_plan": in_plan,
            "audited": audited(k) or "",
        })
    print("round\tdate\tn_rows\tids\tstatus\tin_plan\taudited\ttitle")
    for r in rows:
        print("\t".join([r["id"], r["date"], str(r["n_rows"]), r["ids"], r["st"],
                         str(r["in_plan"]), r["audited"], r["title"]]))

    # ---- gaps
    print("\n# GAPS")
    un = [r for r in rows if not r["audited"]]
    print("# rounds in era: %d, never audited: %d" % (len(rows), len(un)))
    g1 = [r for r in un if r["n_rows"] == 0]
    g2 = [r for r in un if r["n_rows"] > 0 and r["in_plan"] == 0]
    g3 = [r for r in un if r["n_rows"] > 0 and r["in_plan"] > 0]
    print("# A no-ledger (%d): %s" % (len(g1), " ".join(r["id"] for r in g1)))
    print("# B ledger-but-no-plan (%d): %s" % (len(g2), " ".join(r["id"] for r in g2)))
    print("# C both (%d)" % len(g3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
