#!/usr/bin/env python3
"""R95：用当前容器那段日志做逐请求对齐（零停机）。

只取最后一次 "filling the GPU's expert cache" 之后的段（= 当前二进制/配置），避免多版本混杂。
对齐三样：tokens、wall、该次 prefill 的 pick_J 次数（= launch 数），以及相位行里的 gemm 两项。
输出：两参数拟合、wall 与 launches 的相关、每 launch 的开销、以及 gemm 是否随 launches 走。
"""
import re
import statistics as st
from collections import defaultdict

LOG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log"
RE_TOK = re.compile(r"strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms, wall (\d+) ms")
RE_PH = re.compile(r"([a-z][a-z0-9+: /]*?) (\d+) \((\d+\.\d)%\)")


def main():
    lines = open(LOG, errors="replace").read().splitlines()
    start = 0
    for i, l in enumerate(lines):
        if "filling the GPU's expert cache" in l:
            start = i
    seg, launches = [], 0
    for l in lines[start:]:
        if l.startswith("pick_J"):
            launches += 1
            continue
        m = RE_TOK.match(l)
        if m:
            ph = {a.strip(): int(b) for a, b, _ in RE_PH.findall(l.split(":", 1)[1])}
            seg.append(dict(n=int(m.group(1)), gpu=int(m.group(2)), wall=int(m.group(3)),
                            launch=launches, gu=ph.get("gemm gate/up"), dn=ph.get("gemm down")))
            launches = 0
    seg = [s for s in seg if s["launch"] > 0 and s["gu"]]
    print("段数（当前容器）", len(seg))
    ns = [s["n"] for s in seg]
    print("tokens 范围 %d–%d" % (min(ns), max(ns)))

    def fit(xs, ys):
        k = len(xs); mx, my = sum(xs) / k, sum(ys) / k
        a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
        return a, my - a * mx

    def r2(xs, ys, a, b):
        my = sum(ys) / len(ys)
        ss = sum((y - my) ** 2 for y in ys)
        sr = sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))
        return 1 - sr / ss

    W = [s["wall"] for s in seg]; GU = [s["gu"] for s in seg]; DN = [s["dn"] or 0 for s in seg]
    L = [s["launch"] for s in seg]
    for name, ys in (("wall", W), ("gemm gate/up", GU), ("gemm down", DN)):
        a1, b1 = fit(ns, ys); r1 = r2(ns, ys, a1, b1)
        a2, b2 = fit(L, ys); r2v = r2(L, ys, a2, b2)
        print("%-12s vs tokens: a=%.0f us/tok b=%.0f ms R2=%.3f  | vs launches: a=%.3f ms/launch b=%.0f ms R2=%.3f"
              % (name, a1 * 1000, b1, r1, a2, b2, r2v))
    # 相关
    def corr(x, y):
        mx, my = sum(x) / len(x), sum(y) / len(y)
        sx = (sum((i - mx) ** 2 for i in x) / len(x)) ** .5
        sy = (sum((i - my) ** 2 for i in y) / len(y)) ** .5
        return sum((a - mx) * (b - my) for a, b in zip(x, y)) / len(x) / (sx * sy)
    print("corr(wall, launches)=%.2f  corr(wall, tokens)=%.2f  corr(gate/up, launches)=%.2f"
          % (corr(W, L), corr(W, ns), corr(GU, L)))
    # 按长度档
    d = defaultdict(list)
    for s in seg:
        d[int(s["n"] / 2000)].append(s)
    print("\n档   n    tokens   launches  wall   gate/up  down   ms/launch")
    for k in sorted(d):
        v = d[k]
        print("~%dK %-4d %7.0f %9.1f %6.0f %8.0f %5.0f %9.2f"
              % (k, len(v), st.mean(s["n"] for s in v), st.mean(s["launch"] for s in v),
                 st.mean(s["wall"] for s in v), st.mean(s["gu"] for s in v),
                 st.mean(s["dn"] or 0 for s in v),
                 st.mean(s["wall"] for s in v) / st.mean(s["launch"] for s in v)))


if __name__ == "__main__":
    main()
