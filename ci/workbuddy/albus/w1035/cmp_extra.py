"""Extra metrics on top of `quant_quality.py pcompare`, same dumps, no engine.

pcompare answers "top-1 / KL".  For a claim of the form "this patch does not change the
numbers" the decisive quantity is the largest single logit difference, so this prints:

    pair             n   top1%   KLmean   max|dlogit|   identical?

  REF  = pq_001     (production exe)
  FLOOR= pq_001b    (same exe, fresh container -> run-to-run floor)
  GATE = pq_010     (K10)

  python3 cmp_extra.py /w1035/pq_001 /w1035/pq_001b /w1035/pq_010
"""
import pathlib
import sys

import numpy as np


def logp(path):
    x = np.fromfile(path, dtype=np.float32).astype(np.float64)
    x -= x.max()
    return x - np.log(np.exp(x).sum())


def pairs(ref, run):
    kl, agree, dmax, n = [], 0, 0.0, 0
    i = 0
    while True:
        a, b = pathlib.Path(ref) / ("first.%d" % i), pathlib.Path(run) / ("first.%d" % i)
        if not (a.exists() and b.exists()):
            break
        lr, la = logp(a), logp(b)
        pr = np.exp(lr)
        kl.append(float((pr * (lr - la)).sum()))
        agree += int(lr.argmax() == la.argmax())
        dmax = max(dmax, float(np.abs(lr - la).max()))
        n += 1
        i += 1
    return n, 100.0 * agree / max(n, 1), sum(kl) / max(n, 1), dmax


def main():
    ref = sys.argv[1]
    print("%-26s %4s %7s %9s %12s %s" % ("run", "n", "top1%", "KLmean", "max|dlogit|", "identical"))
    for run in sys.argv[2:]:
        n, t1, kl, dm = pairs(ref, run)
        print("%-26s %4d %7.2f %9.5f %12.3e %s" %
              (run.replace("/w1035/", ""), n, t1, kl, dm, "YES" if dm == 0.0 else "no"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
