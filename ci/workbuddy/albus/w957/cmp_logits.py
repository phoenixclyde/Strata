# -*- coding: utf-8 -*-
"""Compare two --dump-logits dumps (float32, one row per logits-stride position).

Prints, per row: argmax ids (both), top-10 overlap, max |diff|, rel_l2, and KL(p||q) on full softmax.
No numpy on the box, so this is plain Python (a few million exp() calls: fine).
Usage: python3 cmp_logits.py A.logits B.logits [vocab]
"""
import array
import math
import sys

VOCAB_DEFAULT = 248320


def load(path):
    a = array.array("f")
    with open(path, "rb") as f:
        a.frombytes(f.read())
    return a


def softmax_kl(r, s):
    m1 = max(r)
    m2 = max(s)
    z1 = sum(math.exp(x - m1) for x in r)
    z2 = sum(math.exp(x - m2) for x in s)
    kl = 0.0
    for x, y in zip(r, s):
        p = math.exp(x - m1) / z1
        q = math.exp(y - m2) / z2
        if p > 1e-12:
            kl += p * math.log(p / q)
    return kl


def main():
    a, b = load(sys.argv[1]), load(sys.argv[2])
    vocab = int(sys.argv[3]) if len(sys.argv) > 3 else VOCAB_DEFAULT
    n = len(a)
    rows = n // vocab if vocab and n % vocab == 0 else 1
    print("floats A=%d B=%d | rows=%d vocab=%d" % (len(a), len(b), rows, n // rows))
    if len(a) != len(b):
        print("SIZE MISMATCH -> not comparable")
        return 2
    for i in range(rows):
        r = a[i * vocab:(i + 1) * vocab]
        s = b[i * vocab:(i + 1) * vocab]
        am_r = max(range(vocab), key=lambda k: r[k])
        am_s = max(range(vocab), key=lambda k: s[k])
        top_r = set(sorted(range(vocab), key=lambda k: -r[k])[:10])
        top_s = set(sorted(range(vocab), key=lambda k: -s[k])[:10])
        md = max(abs(x - y) for x, y in zip(r, s))
        nr = math.sqrt(sum(x * x for x in r))
        rl = math.sqrt(sum((x - y) ** 2 for x, y in zip(r, s))) / (nr if nr else 1)
        print("row %d: argmax %d vs %d %s | top10 %d/10 | max|d|=%.4g | rel_l2=%.6g | KL=%.6g"
              % (i, am_r, am_s, "SAME" if am_r == am_s else "DIFF",
                 len(top_r & top_s), md, rl, softmax_kl(r, s)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
