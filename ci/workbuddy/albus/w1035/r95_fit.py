#!/usr/bin/env python3
"""R95 下一手：把「每 token 成本」拆成 固定项 + 每token项（T = a*n + b）。

输入：albus/w1035/PREFILL_PHASES.tsv（从 166 取回的原文，30 列）。
只取「新 campaign」三档（2083 / 8244 / 16340 tok），因为旧 campaign 形状差 17% 且整体更慢。
输出：每相位的 a（μs/token）、b（ms）、2K 预测与实测误差，以及固定项占比。

用法：python albus/w1035/r95_fit.py
"""
import io
import statistics as st

P = "albus/w1035/PREFILL_PHASES.tsv"
NEW = (2080, 2084, 2086, 8173, 8271, 8289, 16246, 16375, 16400)


def load():
    rows = [l.split("\t") for l in io.open(P, encoding="utf-8").read().splitlines() if l.strip()]
    hdr = rows[0]
    return hdr, [r for r in rows[1:] if int(r[0]) in NEW]


def groups(rows):
    g = {}
    for r in rows:
        g.setdefault(round(int(r[0]) / 1000), []).append(r)
    return sorted((st.mean(int(r[0]) for r in v), v) for k, v in g.items())


def fit(ns, ys):
    k = len(ns)
    mx, my = sum(ns) / k, sum(ys) / k
    a = sum((x - mx) * (y - my) for x, y in zip(ns, ys)) / sum((x - mx) ** 2 for x in ns)
    return a, my - a * mx


def main():
    hdr, rows = load()
    C = {n: hdr.index(n) for n in hdr}
    pts = groups(rows)
    ns = [n for n, _ in pts]
    print("档位:", ["%d" % n for n in ns])
    print("%-16s %11s %10s %10s %10s %9s" % ("相位", "每token(us)", "固定(ms)", "预测2K", "实测2K", "误差"))
    for ph in ("wall_ms", "gemm gate/up", "gemm down", "host grouping", "wait copy",
               "router+shared", "combine", "qsa attn", "dequant"):
        if ph not in C:
            continue
        ys = [st.mean(float(r[C[ph]]) for r in v) for _, v in pts]
        a, b = fit(ns, ys)
        pred = a * ns[0] + b
        print("%-16s %11.1f %10.1f %10.0f %10.0f %8.1f%%"
              % (ph, a * 1000, b, pred, ys[0], (pred - ys[0]) / ys[0] * 100))
    ys = [st.mean(float(r[C["wall_ms"]]) for r in v) for _, v in pts]
    a, b = fit(ns, ys)
    print("\n墙钟固定项 b = %.0f ms，占 2K 实测 %.0f ms 的 %.0f%%"
          % (b, ys[0], 100 * b / ys[0]))


if __name__ == "__main__":
    main()
