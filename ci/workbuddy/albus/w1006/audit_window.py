#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1006 audit: check every claim-bearing round of the unaudited window against the ledger.

Scope: the rounds AUDIT25 stopped before (W986-W1005) plus the coverage holes that the
AUDIT_INDEX table leaves (W854 / W898 / W899).  For each round it extracts the ids it claims
(P/R numbers), the decision verbs, and then asks the ledger whether the id exists, whether its
status matches the verb, and whether the plan ever mentions the round.

The point is to catch the two failure modes the earlier audits kept finding:
  * a decision written in the log that never became a ledger row ("说完了，没上账")
  * an id quoted as if it existed that the ledger has never heard of
"""
import io
import os
import re
import sys

W = r"D:/workbuddy_space/strata_ws"
MEM = os.path.join(W, ".workbuddy/memory")
PLAN = os.path.join(W, "deploy/W832_OPT_PLAN_V2.md")
PROG = os.path.join(W, "deploy/PROGRESS.tsv")

RANGE = list(range(986, 1006)) + [854, 898, 899]
DECIDE = {
    "ADOPT": ["采纳", "上了生产", "已落产", "切到", "上生产"],
    "REJECT": ["判否", "判死", "判否", "回退", "撤", "不动", "别做"],
    "CLOSE": ["结案", "结项", "关闭", "已关", "收口"],
}


def sections():
    """round id -> text (its own section, up to the next '## ' heading)"""
    out = {}
    for f in sorted(os.listdir(MEM)):
        if not f.startswith("2026-") or not f.endswith(".md"):
            continue
        txt = io.open(os.path.join(MEM, f), encoding="utf-8", errors="replace").read()
        parts = re.split(r"(?m)^(##\s+.*)$", txt)
        for i in range(1, len(parts), 2):
            head, body = parts[i], parts[i + 1] if i + 1 < len(parts) else ""
            for n in set(int(x) for x in re.findall(r"\bW(\d{3,4})\b", head)):
                if n in RANGE and n not in out:
                    out[n] = head + "\n" + body
    return out


def ledger():
    rows = [l.rstrip("\n").split("\t") for l in io.open(PROG, encoding="utf-8")
            if l.strip() and not l.startswith("#")]
    h = rows[0]
    ii, si, st = h.index("id"), h.index("source"), h.index("status")
    d = {}
    for r in rows[1:]:
        if len(r) <= max(ii, si, st):
            continue
        d.setdefault(r[ii], {"status": r[st], "source": r[si], "item": r[2]})
    return d


def main():
    S, L = sections(), ledger()
    P = io.open(PLAN, encoding="utf-8").read()
    print("round\tids_claimed\tmissing_in_ledger\tplan_hits\tverbs")
    problems = []
    for n in sorted(RANGE):
        if n not in S:
            continue
        t = S[n]
        ids = sorted(set(re.findall(r"\b([PR]\d{1,3}[a-z]?)\b", t)))
        miss = [i for i in ids if i not in L]
        verbs = []
        for k, ws in DECIDE.items():
            if any(w in t for w in ws):
                verbs.append(k)
        hits = len(re.findall(r"\bW%d\b" % n, P))
        print("W%d\t%s\t%s\t%d\t%s" % (n, ",".join(ids) or "-", ",".join(miss) or "-", hits,
                                       "/".join(verbs) or "-"))
        if miss:
            problems.append(("missing", n, miss))
        if verbs and hits == 0:
            problems.append(("no-plan", n, verbs))
    print("\n# PROBLEMS")
    for kind, n, x in problems:
        print("%-9s W%d %s" % (kind, n, x))
    return 0


if __name__ == "__main__":
    sys.exit(main())
