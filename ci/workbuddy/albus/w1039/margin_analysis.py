#!/usr/bin/env python3
"""W1039: where does the dp4a top-1 loss actually sit?  Read the two runs' TSVs and look at the margins of the
positions whose argmax changed.  A change with a 0.02-nat margin is cosmetic; a change with a 2-nat margin is real."""
import io
import sys


def load(path):
    rows = []
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            f = ln.rstrip("\n").split("\t")
            if len(f) < 8 + 8:
                continue
            try:
                pos = int(f[0])
                tgt = int(f[1])
                lp_t = float(f[2])
                am = int(f[3])
                lp_am = float(f[4])
            except ValueError:
                continue
            top = []
            for x in f[8:8 + 64]:
                if ":" in x:
                    a, b = x.split(":", 1)
                    try:
                        top.append((int(a), float(b)))
                    except ValueError:
                        pass
            top.sort(key=lambda z: -z[1])
            rows.append(dict(pos=pos, tgt=tgt, lp_t=lp_t, am=am, lp_am=lp_am, top=top))
    return rows


def main():
    A = load(sys.argv[1])
    B = load(sys.argv[2])
    n = min(len(A), len(B))
    print("rows A=%d B=%d, compared=%d" % (len(A), len(B), n))

    changed = 0
    margins = []
    rank_of_A_in_B = []
    tgt_lp_delta = []
    for i in range(n):
        a, b = A[i], B[i]
        if a["pos"] != b["pos"]:
            print("pos mismatch at row", i, a["pos"], b["pos"])
            break
        tgt_lp_delta.append(abs(a["lp_t"] - b["lp_t"]))
        if a["am"] == b["am"]:
            continue
        changed += 1
        # margin of the reference distribution at that position: top1 - top2
        if len(a["top"]) >= 2:
            margins.append(a["top"][0][1] - a["top"][1][1])
        # where did A's argmax sit in B's list?
        ids_b = [t[0] for t in b["top"]]
        rank_of_A_in_B.append(ids_b.index(a["am"]) + 1 if a["am"] in ids_b else 99)

    print("argmax changed: %d / %d = %.2f%%" % (changed, n, 100.0 * changed / n))
    if margins:
        margins.sort()
        print("reference margin (top1-top2, nats) at changed positions:")
        for q in (10, 25, 50, 75, 90, 99):
            print("   p%-3d %.4f" % (q, margins[min(len(margins) - 1, int(q / 100.0 * len(margins)))]))
        for thr in (0.01, 0.05, 0.1, 0.5, 1.0, 2.0):
            c = sum(1 for m in margins if m < thr)
            print("   margin < %.2f nats: %5d (%.1f%% of changed, %.2f%% of all)" % (
                thr, c, 100.0 * c / len(margins), 100.0 * c / n))
    if rank_of_A_in_B:
        from collections import Counter
        c = Counter(rank_of_A_in_B)
        print("rank of A's argmax inside B's top-64:", sorted(c.items())[:8], "... not-in-64:",
              c.get(99, 0))

    tgt_lp_delta.sort()
    print("|Δ logp(target)|: median %.4f  p90 %.4f  max %.4f" % (
        tgt_lp_delta[len(tgt_lp_delta) // 2], tgt_lp_delta[int(0.9 * len(tgt_lp_delta))], tgt_lp_delta[-1]))


if __name__ == "__main__":
    main()
