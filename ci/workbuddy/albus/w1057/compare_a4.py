#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1057/R74: compare STRATA_DUMP_FIRST_LOGITS dumps (248320 float32 each).
# Pairs: A1a-A1b = cross-process noise floor; A1a-A2 = patch-inert; A1a-B = the R74 gate.
import array
import math
import os
import sys

D = sys.argv[1] if len(sys.argv) > 1 else "/home/albus/strata166/data/w1057"
VOCAB_EXPECT = 248320
N = 6


def load(tag, i):
    p = os.path.join(D, "fl_%s.%d" % (tag, i))
    if not os.path.isfile(p):
        return None
    a = array.array("f")
    with open(p, "rb") as f:
        a.frombytes(f.read())
    return a


def softmax(x):
    m = max(x)
    e = [math.exp(v - m) for v in x]
    s = sum(e)
    return [v / s for v in e], math.log(s) + m


def kl(p, q):
    # KL(softmax(p) || softmax(q)) computed stably from logits
    ep, lp = softmax(p)
    eq, lq = softmax(q)
    acc = 0.0
    for a, b in zip(ep, eq):
        if a > 0:
            acc += a * (math.log(a) - math.log(b))
    return acc


def top1(x):
    b, bi = x[0], 0
    for i, v in enumerate(x):
        if v > b:
            b, bi = v, i
    return bi


def cmp_pair(t1, t2):
    rows = []
    for i in range(N):
        a, b = load(t1, i), load(t2, i)
        if a is None or b is None:
            print("MISSING %s.%d or %s.%d" % (t1, i, t2, i))
            continue
        assert len(a) == len(b), (len(a), len(b))
        k = kl(a, b)
        t = 1 if top1(a) == top1(b) else 0
        md = max(abs(x - y) for x, y in zip(a, b))
        rows.append((i, k, t, md, len(a)))
    if not rows:
        return
    ks = [r[1] for r in rows]
    ts = sum(r[2] for r in rows)
    mds = [r[3] for r in rows]
    print("PAIR %s vs %s : n=%d  KL mean %.6f max %.6f | top1 %d/%d = %.1f%% | max|dl| mean %.4f max %.4f | vocab %d"
          % (t1, t2, len(rows), sum(ks) / len(ks), max(ks), ts, len(rows), 100.0 * ts / len(rows),
             sum(mds) / len(mds), max(mds), rows[0][4]))
    for r in rows:
        print("   req%d KL %.6f top1 %d max|dl| %.4f" % (r[0], r[1], r[2], r[3]))
    return sum(ks) / len(ks), max(ks), ts / len(rows)


print("== R74 W4A4 activation precision gate (STRATA_A4_SIM) ==")
f = cmp_pair("A1a", "A1b")
g = cmp_pair("A1a", "A2")
gate = cmp_pair("A1a", "B")
cmp_pair("A2", "B")
if gate:
    kmean, kmax, t1 = gate
    ok = (kmean <= 0.005) and (t1 >= 0.99)
    print("VERDICT_GATE kl_mean=%.6f (<=0.005 %s) top1=%.1f%% (>=99%% %s) => %s"
          % (kmean, kmean <= 0.005, t1 * 100, t1 >= 0.99, "PASS" if ok else "FAIL"))
if f:
    print("FLOOR cross-process kl_mean=%.6f (resolution ref 0.0032)" % f[0])
if g:
    print("INERT a4probe-noenv vs hc4b kl_mean=%.6f (patch must be numerically inert)" % g[0])
