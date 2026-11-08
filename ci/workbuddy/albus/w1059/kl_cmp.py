#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1059: kl_prop compare for the LOGPOS window (W824/W913 口径, kl_pair2.py's kl_prop verbatim).
# Pairs: floor (s001a,s001b must be 0) / P392 stack (s010 vs s001a) / R101 single (sum1 vs sum0).
import hashlib
import io
import math
import os
import statistics as st
import sys

D = sys.argv[1] if len(sys.argv) > 1 else "/home/albus/strata166/data/w1059"


def load(arm):
    rows = {}
    p = os.path.join(D, "logpos_%s.tsv" % arm)
    with io.open(p, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            c = line.split("\t")
            topk = {}
            for x in c[8:]:
                if ":" in x:
                    i, v = x.split(":", 1)
                    topk[int(i)] = float(v)
            rows[int(c[0])] = {"tgt": int(c[1]), "lp_tgt": float(c[2]),
                               "top": int(c[3]), "topk": topk}
    return rows


def kl_prop(P, Q):
    sp, sq = set(P["topk"]), set(Q["topk"])
    if not sp or not sq:
        return None
    pp = {t: math.exp(P["topk"][t]) for t in sp}
    qq = {t: math.exp(Q["topk"][t]) for t in sq}
    rq = max(0.0, 1.0 - sum(qq.values()))
    missing = sp - sq
    sm = sum(pp[t] for t in missing)
    kl = 0.0
    for t in sp:
        p = pp[t]
        if p <= 0:
            continue
        if t in sq:
            q = qq[t]
        else:
            q = rq * (pp[t] / sm) if sm > 0 else rq / max(1, len(missing))
        kl += p * math.log(p / max(q, 1e-300))
    return kl


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


ARMS = ["s001a", "s001b", "s010", "sum0", "sum1"]
print("== files")
for a in ARMS:
    p = os.path.join(D, "logpos_%s.tsv" % a)
    ok = os.path.isfile(p)
    print("  %-6s %s  rows=%d  md5=%s" % (
        a, "OK" if ok else "MISSING",
        len(load(a)) if ok else 0, md5(p)[:12] if ok else "-"))

PAIRS = [
    ("floor?", "s001a", "s001b", "same binary twice -> must be 0 (suspect profile confound)"),
    ("profile", "s001a", "s001b", "first-arm profile-generation effect (expect nonzero)"),
    ("P392 stack", "s010", "s001b", "K10 stack vs baseline (both profile-loaded)"),
    ("P392 raw", "s010", "s001a", "K10 vs first-arm (confounded, reference only)"),
    ("R101 sum", "sum1", "sum0", "Sigma-x vs d*Sigma-q (single variable)"),
]
print("\n== kl_prop (P=first, mean/top1)")
for name, pa, pb, note in PAIRS:
    A, B = load(pa), load(pb)
    common = sorted(set(A) & set(B))
    kls = [kl_prop(A[p], B[p]) for p in common]
    kls = [k for k in kls if k is not None]
    top1 = sum(1 for p in common if A[p]["top"] == B[p]["top"])
    maxk = max(kls) if kls else float("nan")
    meank = st.mean(kls) if kls else float("nan")
    same_md5 = md5(os.path.join(D, "logpos_%s.tsv" % pa)) == md5(os.path.join(D, "logpos_%s.tsv" % pb))
    print("  %-12s %s vs %s  n=%d  KL mean=%.6f max=%.6f  top1=%d/%d  md5same=%s" % (
        name, pa, pb, len(kls), meank, maxk, top1, len(common), same_md5))
    print("      note: %s" % note)
    if name == "floor":
        verdict = "PASS" if (meank == 0.0 and top1 == len(common)) else "FAIL"
        print("      floor verdict: %s (must be exactly 0)" % verdict)
    if name == "R101 sum" and same_md5:
        print("      !! md5 identical -> env gate dead / bypassed (W1057 lesson)")
