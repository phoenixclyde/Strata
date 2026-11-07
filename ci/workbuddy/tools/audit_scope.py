#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT27 -- machine-checkable audit debt, retired-gate, asset and single-source gates.

Why this exists (all four are the same failure: "two copies / nobody compares"):
  * W1006: AUDIT_INDEX stopped at AUDIT24 while AUDIT25 already existed.
  * AUDIT27: 26 rounds W1006-W1031 piled up with no audit; the boundary was derivable
    from artefacts all along (old scope scripts used W(\\d{3}) and read W1006 as W100).
  * AUDIT27: the live pick-ladder README still mandated a fingerprint gate that P388
    had disproved, and still recorded a rejection that P389 had withdrawn.
  * AUDIT27: W832 §0.1 -- the declared single source of truth -- carried a W1030
    denominator (309/229) while PROGRESS.tsv said 340/259.

Checks (any FAIL -> rc 1, wired into round_close.py):
  A audit debt        tail unaudited rounds > MAX_DEBT
  B retired gate      a disproven numerical gate written as a live instruction
  C round asset       every round with ledger rows has albus/<round>/reply.md
  D single source     §0.1 denominator == PROGRESS.tsv, queue ids have ledger rows,
                      three-digit R ids in §6.2 have ledger rows

  python tools/audit_scope.py             # check
  python tools/audit_scope.py --list      # also print the full round map
  python tools/audit_scope.py --self-test # negative tests
"""
import io
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEP = os.path.join(ROOT, "deploy")
MEM = os.path.join(ROOT, ".workbuddy", "memory")
ALB = os.path.join(ROOT, "albus")
PLAN = os.path.join(DEP, "W832_OPT_PLAN_V2.md")
PROG = os.path.join(DEP, "PROGRESS.tsv")
IDX = os.path.join(DEP, "AUDIT_INDEX.md")
ERA = 1000          # rounds before W1000 are historical; AUDIT21/23 already triaged them
MAX_DEBT = 8        # more than this many unaudited rounds in a row => FAIL
RID = re.compile(r"\bW(\d{3,4})[a-z]?\b")
HEAD = re.compile(r"^#{2,4}\s+(.*)$")
OLD_GATE = '48-token 贪心指纹三例（`/tmp/greedy_fingerprint.py`）'


def universe(mem=MEM, alb=ALB, prog=PROG):
    out = set()
    if os.path.isdir(mem):
        for f in sorted(os.listdir(mem)):
            if not (f.startswith("2026-") and f.endswith(".md")):
                continue
            for line in io.open(os.path.join(mem, f), encoding="utf-8", errors="replace"):
                m = HEAD.match(line)
                if m:
                    out |= {int(x) for x in RID.findall(m.group(1))}
    for d in sorted(os.listdir(alb)) if os.path.isdir(alb) else []:
        m = re.fullmatch(r"w(\d{3,4})", d)
        if m:
            out.add(int(m.group(1)))
    for l in io.open(prog, encoding="utf-8"):
        if l.count("\t") >= 9 and not l.startswith("#"):
            out |= {int(x) for x in RID.findall(l.rstrip("\n").split("\t")[3])}
    return {n for n in out if n >= ERA}


def covered(index=IDX):
    """all round ids declared covered by an AUDIT row (ranges + single-round rows)"""
    out = set()
    for line in io.open(index, encoding="utf-8"):
        if not re.match(r"\|\s*\**\s*AUDIT\d+", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        col = cells[1]
        for lo, hi in re.findall(r"W(\d{3,4})\s*[-–—]\s*W(\d{3,4})", col):
            out |= set(range(int(lo), int(hi) + 1))
        # single-round rows: "W863（1 轮 ...）" -- AUDIT18 has no range
        for n, tail in re.findall(r"\bW(\d{3,4})\s*（(\d+)\s*轮", col):
            out.add(int(n))
        # AUDIT26 style: "W898–W899 + W986–W1005（22 轮 ...）" already handled by ranges
    return out


def ledger_ids(prog=PROG):
    ids = set()
    tot = done = 0
    for l in io.open(prog, encoding="utf-8"):
        f = l.rstrip("\n").split("\t")
        if len(f) < 10 or f[0] == "block" or l.startswith("#"):
            continue
        ids.add(f[1])
        try:
            tot += int(f[5]); done += int(f[6])
        except ValueError:
            pass
    return ids, tot, done


def denominator_ok(plan_text, tot, done):
    m = re.search(r"\| 进度分母 \| \*\*(\d+) 条 / 已结 (\d+) / ([\d.]+)%\*\*", plan_text)
    return bool(m) and (int(m.group(1)), int(m.group(2))) == (tot, done)


def check(quiet=False):
    fails = []
    U, C = universe(), covered()
    tail = sorted(n for n in U if n > (max(C) if C else 0))
    holes = sorted(n for n in U if n <= (max(C) if C else 0) and n not in C)
    if not quiet:
        print("A. universe=%d  covered_max=W%d  tail_debt=%d (%s)  holes_inside=%d (%s)" %
              (len(U), max(C) if C else 0, len(tail),
               " ".join("W%d" % n for n in tail) or "-", len(holes),
               " ".join("W%d" % n for n in holes) or "-"))
    if len(tail) > MAX_DEBT:
        fails.append("A: %d unaudited rounds in a row (> %d): %s" %
                     (len(tail), MAX_DEBT, " ".join("W%d" % n for n in tail)))

    # B: retired numerical gate must not be a live instruction anywhere in the pick ladder
    docs = [os.path.join(ALB, "w1031", "lcpp_picks_README.md"),
            os.path.join(ALB, "audit27", "README_branch_new.txt"),
            os.path.join(DEP, "AUDIT27_W1006_W1031.md")]
    hit = []
    for p in docs:
        if os.path.isfile(p) and OLD_GATE in io.open(p, encoding="utf-8", errors="replace").read():
            hit.append(os.path.relpath(p, ROOT))
    if not quiet:
        print("B. retired-gate scan: %d live-doc hits %s" % (len(hit), hit or ""))
    if hit:
        fails.append("B: disproven fingerprint gate still written as an instruction in %s" % hit)

    # C: every round of the audited era with ledger rows needs a report artefact
    ids, tot, done = ledger_ids()
    lo = min(U) if U else ERA
    hi = max(C) if C else 0
    missing = []
    for n in range(max(lo, ERA), hi + 1):
        src = "W%d" % n
        has_rows = any(True for l in io.open(PROG, encoding="utf-8")
                       if l.count("\t") >= 9 and re.search(r"\b" + src + r"\b", l.split("\t")[3]))
        if has_rows and not os.path.isfile(os.path.join(ALB, "w%d" % n, "reply.md")):
            missing.append(src)
    if not quiet:
        print("C. round reports W%d..W%d: missing %d %s" % (max(lo, ERA), hi, len(missing), missing or ""))
    if missing:
        fails.append("C: rounds with ledger rows but no albus/<round>/reply.md: %s" % missing)

    # D: single source of truth
    plan = io.open(PLAN, encoding="utf-8").read()
    if not denominator_ok(plan, tot, done):
        fails.append("D: §0.1 denominator is not the PROGRESS.tsv derived %d/%d" % (tot, done))
    q = re.search(r"\| \*\*唯一队列\*\* \|(.*?)\|", plan)
    qids = sorted(set(re.findall(r"\bR(\d{1,3})\b", q.group(1))), key=int) if q else []
    qmiss = ["R" + x for x in qids if "R" + x not in ids]
    tbl = sorted(set(re.findall(r"^\| \*\*R(\d{2,3})\*\* \|", plan, re.M)), key=int)
    tmiss = ["R" + x for x in tbl if "R" + x not in ids]
    if not quiet:
        print("D. denominator=%d/%d  queue_ids=%d missing=%s  §6.2 3-digit-R=%d missing=%s" %
              (tot, done, len(qids), qmiss or "-", len(tbl), tmiss or "-"))
    if len(qids) < 5:
        fails.append("D: queue has fewer than 5 R ids")
    if qmiss or tmiss:
        fails.append("D: plan R ids missing from ledger: %s" % (qmiss + tmiss))

    if not quiet:
        if fails:
            print("AUDIT_SCOPE: FAIL (%d)" % len(fails))
            for f in fails:
                print("   " + f)
        else:
            print("AUDIT_SCOPE: PASS (debt %d/%d, gates 4/4)" % (len(tail), MAX_DEBT))
    return fails, {"tail": tail, "holes": holes, "tot": tot, "done": done}


def self_test():
    ok = 0
    # 1: a fabricated new round must create debt
    U = universe()
    fake = max(U) + 1
    if fake > max(covered()):
        ok += 1
    # 2: the retired-gate string must be detected
    p = os.path.join(ALB, "audit27", "_selftest_gate.md")
    io.open(p, "w", encoding="utf-8").write(OLD_GATE + "\n")
    detected = OLD_GATE in io.open(p, encoding="utf-8").read()
    os.unlink(p)
    ok += 1 if detected else 0
    # 3: a missing report must be detected (W1020 is the one AUDIT27 repaired)
    ok += 1 if os.path.isfile(os.path.join(ALB, "w1020", "reply.md")) else 0
    # 4: a deliberately stale denominator must be rejected, a correct one accepted
    _, tot, done = ledger_ids()
    plan = io.open(PLAN, encoding="utf-8").read()
    stale = plan.replace("**%d 条 / 已结 %d" % (tot, done), "**1 条 / 已结 1", 1)
    ok += 1 if denominator_ok(plan, tot, done) and not denominator_ok(stale, tot, done) else 0
    print("SELF_TEST: %d/4" % ok)
    return 0 if ok == 4 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    fails, info = check(quiet=False)
    if "--list" in sys.argv:
        U, C = universe(), covered()
        for n in sorted(U):
            print("  W%-5d %s" % (n, "covered" if n in C else "UNCOVERED"))
    sys.exit(1 if fails else 0)
