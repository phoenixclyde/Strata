#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT27 scope: derive the set of rounds that no audit has ever covered.

Do NOT trust the AUDIT_INDEX table to tell you the answer -- derive the boundary from
artefacts (memory headings, deploy/W*.md filenames, PROGRESS.tsv sources), then
subtract the coverage claimed by every AUDIT*.md / *AUDIT*.md artefact.

Supports 4-digit round ids (W1000+).  Earlier scope scripts used W(\\d{3}) and
silently read W1006 as W100, so they cannot be used for this window.

  python albus/audit27/scope.py            # human readable
  python albus/audit27/scope.py --json     # machine readable
"""
import io
import json
import os
import re
import sys
from collections import defaultdict

W = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MEM = os.path.join(W, ".workbuddy", "memory")
DEP = os.path.join(W, "deploy")
PROG = os.path.join(DEP, "PROGRESS.tsv")
IDX = os.path.join(DEP, "AUDIT_INDEX.md")

RID = re.compile(r"\bW(\d{3,4})[a-z]?\b")
HEAD = re.compile(r"^#{2,4}\s+(.*)$")
ART = re.compile(r"^(?:AUDIT\d+_.*|.*(?:AUDIT|REVIEW|VERDICT).*)\.md$", re.I)


def mem_rounds():
    out = defaultdict(list)
    for f in sorted(os.listdir(MEM)):
        if not (f.startswith("2026-") and f.endswith(".md")):
            continue
        for ln, line in enumerate(io.open(os.path.join(MEM, f), encoding="utf-8", errors="replace"), 1):
            m = HEAD.match(line)
            if not m:
                continue
            for x in set(RID.findall(m.group(1))):
                out[int(x)].append("%s:%d %s" % (f, ln, m.group(1).strip()[:78]))
    return out


def file_rounds():
    out = defaultdict(list)
    for f in sorted(os.listdir(DEP)):
        if not f.endswith(".md"):
            continue
        for x in set(RID.findall(f)):
            out[int(x)].append(f)
    return out


def ledger_rounds():
    out = defaultdict(list)
    rows = [l.rstrip("\n").split("\t") for l in io.open(PROG, encoding="utf-8")
            if l.strip() and not l.startswith("#")]
    h = rows[0]
    si, ii, st = h.index("source"), h.index("id"), h.index("status")
    for r in rows[1:]:
        if len(r) <= max(si, ii, st):
            continue
        for x in set(RID.findall(r[si])):
            out[int(x)].append("%s/%s" % (r[ii], r[st]))
    return out, rows


def audits():
    return sorted(f for f in os.listdir(DEP) if ART.match(f) and f.endswith(".md"))


def audit_mentions():
    """round id -> list of audit artefacts whose FULL TEXT names it"""
    out = defaultdict(list)
    for a in audits():
        txt = io.open(os.path.join(DEP, a), encoding="utf-8", errors="replace").read()
        for x in set(RID.findall(txt)):
            out[int(x)].append(a)
    return out


def index_ranges():
    """Parse the coverage column of AUDIT_INDEX.md: W<number>-W<number> ranges."""
    segs = []
    for line in io.open(IDX, encoding="utf-8"):
        if not re.match(r"\|\s*\**\s*AUDIT\d+", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        label = re.search(r"AUDIT(\d+)", cells[0])
        if not label:
            continue
        a, b = cells[0].strip(), cells[1]
        pairs = re.findall(r"W(\d{3,4})\s*[-–—]\s*W(\d{3,4})", b)
        for lo, hi in pairs:
            segs.append((int(label.group(1)), int(lo), int(hi), a, b[:70]))
    return segs


def main():
    M, F = mem_rounds(), file_rounds()
    L, rows = ledger_rounds()
    A = audit_mentions()
    segs = index_ranges()
    covered_by_table = set()
    for _, lo, hi, _, _ in segs:
        covered_by_table.update(range(lo, hi + 1))

    universe = sorted(set(M) | set(F) | set(L))
    unaudited = [n for n in universe if n not in covered_by_table]
    # anything an audit artefact names in full text is at least "touched"; report separately
    touched = [n for n in unaudited if n in A]

    if "--json" in sys.argv:
        print(json.dumps({
            "universe": universe, "index_ranges": [(a, lo, hi, s) for a, lo, hi, _, s in segs],
            "covered": sorted(covered_by_table),
            "unaudited": unaudited, "touched_by_audit_text": touched,
            "audits": audits(),
        }, ensure_ascii=False, indent=1))
        return 0

    print("=== audit artefacts (%d) ===" % len(audits()))
    for a in audits():
        print("   " + a)
    print("\n=== AUDIT_INDEX coverage ranges (%d) ===" % len(segs))
    for a, lo, hi, _, s in segs:
        print("   AUDIT%-3d W%d-W%d   %s" % (a, lo, hi, s))
    print("\n=== universe: %d rounds, W%d..W%d ===" % (len(universe), universe[0], universe[-1]))
    print("=== never covered by any index range: %d ===" % len(unaudited))
    for n in unaudited:
        print("W%-5d mem=%-2d docs=%-3d ledger=%-3d audit_text=%s" %
              (n, len(M.get(n, [])), len(F.get(n, [])), len(L.get(n, [])),
               ",".join(A.get(n, []))[:60] or "-"))
    print("\n=== of those, named in some audit full text (need judgement): %d ===" % len(touched))
    print("   " + " ".join("W%d" % n for n in touched))
    return 0


if __name__ == "__main__":
    sys.exit(main())
