#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ci/rebase_oracle.py -- what did this rebase lose that a clean merge keeps?

Why this exists (W1176): `git rebase --onto` resolved two conflicts with
`checkout --theirs`, so engine/src/program/generate.cpp and
engine/src/prefill/prefill.cpp became the OLD branch copies -- 1,973 lines of
our own work vanished while every static check stayed green.  `git cherry`
cannot see it (the patch is still "there", it just replaced other text) and a
compile gate cannot see it either (the old file compiles).  The only honest
measure is:

    M = git merge-tree --write-tree A U     # what a clean merge produces
    lost = lines in M that B does not have  # B = what the rebase shipped

Usage
    python ci/rebase_oracle.py --a 24eefda5d --u v0.2.18 --b HEAD
    python ci/rebase_oracle.py --a <sha> --u <tag> --threshold 300 --json

Exit codes
    0  under the threshold (or exactly the documented baseline)
    1  over the threshold -- stop and adjudicate file by file
    2  usage / git error

A file present in M and absent from B is resolved through a unique basename
(the 0.2.16 layout move put src/ under engine/src/).  Files that the merge
itself reports as conflicted are counted separately: their content is a
conflict-marked draft, not a merge result, so their line diff is noise.
"""
import argparse
import collections
import json
import os
import subprocess
import sys

MINLEN = 12
REPO = "."


def git(*args, cwd=None):
    p = subprocess.run(["git"] + list(args), cwd=cwd or REPO, capture_output=True, text=True,
                       errors="replace")
    return p.returncode, p.stdout


def tree_map(ref):
    rc, out = git("ls-tree", "-r", ref)
    if rc != 0:
        return None
    d = {}
    for line in out.splitlines():
        meta, path = line.split("\t", 1)
        d[path] = meta.split()[2]
    return d


def lines_of(tree, path):
    rc, out = git("show", "%s:%s" % (tree, path))
    if rc != 0:
        return set()
    return {x.strip() for x in out.splitlines() if len(x.strip()) >= MINLEN}


def resolve_path(ref_map, path, name_index=None):
    """Map a path in one tree onto the other tree's layout.

    0.2.16 moved src/ -> engine/src/ and sycl/src/ -> engine/sycl/src/, so a plain
    path lookup misses exactly the two files a replay clobbers.  Try the layout
    prefix first (unambiguous), then a unique basename.
    """
    if path in ref_map:
        return path
    if path.startswith("engine/") and path[7:] in ref_map:
        return path[7:]
    if ("engine/" + path) in ref_map:
        return "engine/" + path
    if name_index is not None:
        return name_index.get(path.rsplit("/", 1)[-1])
    return None


def unique_basename_index(m):
    idx = collections.defaultdict(list)
    for p in m:
        idx[p.rsplit("/", 1)[-1]].append(p)
    return {k: v[0] for k, v in idx.items() if len(v) == 1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="branch tip before the rebase")
    ap.add_argument("--u", required=True, help="upstream base the rebase moved onto")
    ap.add_argument("--b", default="HEAD", help="what the rebase actually shipped")
    ap.add_argument("--threshold", type=int, default=300,
                    help="fail when the total lost-line count exceeds this (default 300)")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--repo", default=".")
    a = ap.parse_args()
    global REPO
    REPO = a.repo

    for ref in (a.a, a.u, a.b):
        rc, _ = git("rev-parse", "--verify", ref + "^{commit}", cwd=a.repo)
        if rc != 0:
            print("cannot resolve %r" % ref, file=sys.stderr)
            return 2

    rc, out = git("merge-tree", "--write-tree", a.a, a.u, cwd=a.repo)
    if rc not in (0, 1) or not out.strip():
        print("git merge-tree failed rc=%d" % rc, file=sys.stderr)
        return 2
    rows = out.splitlines()
    merge_tree = rows[0].strip()
    conflicted = sorted({l.split("\t")[-1] for l in rows[1:] if "\t" in l})

    mm = tree_map(merge_tree)
    mb = tree_map(a.b)
    if mm is None or mb is None:
        print("cannot read the merge tree or B", file=sys.stderr)
        return 2
    byname = unique_basename_index(mb)

    per_file, absent, total = [], [], 0
    for path in mm:
        if path in conflicted:
            continue
        target = resolve_path(mb, path, byname)
        if target is None:
            absent.append(path)
            continue
        if mb[target] == mm[path]:
            continue
        lost = len(lines_of(merge_tree, path) - lines_of(a.b, target))
        if lost:
            per_file.append((lost, path if target == path else "%s <- %s" % (target, path)))
    per_file.sort(key=lambda r: -r[0])
    total = sum(r[0] for r in per_file)

    # The conflicted files are excluded above, and in W1176 BOTH files that lost
    # 1,703 lines were exactly the conflicted ones -- excluding them hid the loss.
    # So add a second, conflict-proof signal: a file whose B copy still matches the
    # OLD branch's copy (<=5 differing lines) while upstream's copy is >=300 lines
    # bigger was reverted wholesale.  Candidates come from one `diff --numstat U B`
    # run, so the cost is bounded by the files that actually shrank.
    rc, out = git("diff", "--numstat", a.u, a.b, cwd=a.repo)
    cands = []
    if rc == 0:
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) != 3 or parts[1] == "-":
                continue
            if int(parts[1]) >= 300:
                cands.append((int(parts[1]), parts[2]))
    ma = tree_map(a.a)
    mu = tree_map(a.u)
    a_name = unique_basename_index(ma) if ma else {}
    u_name = unique_basename_index(mu) if mu else {}
    hard = []
    for dele, path in cands:
        if path.startswith(("engine/third_party/", "third_party/")):
            continue
        src = resolve_path(ma, path, a_name) if ma else None
        up = resolve_path(mu, path, u_name) if mu else None
        if not src or not up:
            continue
        if len(lines_of(a.a, src) - lines_of(a.b, path)) <= 5:
            hard.append((dele, path))
    hard.sort(key=lambda r: -r[0])
    verdict = "PASS" if (total <= a.threshold and not hard) else "FAIL"
    if a.json:
        print(json.dumps({"a": a.a, "u": a.u, "b": a.b, "merge_tree": merge_tree,
                          "conflicted": len(conflicted), "total_lost_lines": total,
                          "reverted_hard": [{"lost": n, "path": p} for n, p in hard],
                          "threshold": a.threshold, "verdict": verdict,
                          "files": [{"lost": n, "path": p} for n, p in per_file]},
                         ensure_ascii=False, indent=1))
        return 0 if verdict == "PASS" else 1

    print("rebase oracle: A=%s  U=%s  =>  merge %s   vs shipped B=%s"
          % (a.a[:10], a.u[:10], merge_tree[:10], a.b[:10]))
    print("conflicted files in the merge: %d (excluded: their merge content is a draft)" % len(conflicted))
    print("total lines a clean merge keeps and the rebase does not: %d (threshold %d)"
          % (total, a.threshold))
    print("%8s  %s" % ("lost", "path"))
    for n, p in per_file[:a.top]:
        print("%8d  %s" % (n, p))
    if len(per_file) > a.top:
        print("   ... %d more files" % (len(per_file) - a.top))
    if hard:
        print("REVERTED WHOLE FILES (B still matches A, upstream has >=300 more lines): %d" % len(hard))
        for n, p in hard[:a.top]:
            print("   %6d  %s" % (n, p))
    if absent:
        print("files absent from B with no counterpart: %d" % len(absent))
        for p in absent[:8]:
            print("   ", p)
    print("VERDICT: %s" % verdict)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
