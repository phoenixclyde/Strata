#!/usr/bin/env python3
"""R95：逐相位的「每 token 成本」排序（当前容器，8 个长度点，零停机）。

对每个相位做 T = a·n + b，按 a 降序输出；同时给出该相位占 wall 斜率 1.24 ms/tok 的份额。
只取最后一次 "filling the GPU's expert cache" 之后的段，避免多版本混杂。
"""
import re
import statistics as st

LOG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log"
RE_TOK = re.compile(r"strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms, wall (\d+) ms")
RE_PH = re.compile(r"([a-z][a-z0-9+: /]*?) (\d+) \((\d+\.\d)%\)")


def fit(xs, ys):
    k = len(xs)
    mx, my = sum(xs) / k, sum(ys) / k
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return 0.0, my
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    return a, my - a * mx


def main():
    lines = open(LOG, errors="replace").read().splitlines()
    start = max((i for i, l in enumerate(lines) if "filling the GPU's expert cache" in l), default=0)
    rows = []
    for l in lines[start:]:
        m = RE_TOK.match(l)
        if m:
            ph = {a.strip(): int(b) for a, b, _ in RE_PH.findall(l.split(":", 1)[1])}
            rows.append((int(m.group(1)), int(m.group(3)), ph))
    # 只保留长度分散的干净点：同一 tokens 重复的取均值前先去重
    rows.sort(key=lambda r: r[0])
    keep, seen = [], set()
    for n, w, ph in rows:
        if n in seen:
            continue
        seen.add(n)
        keep.append((n, w, ph))
    print("干净点数 %d，tokens %d–%d" % (len(keep), keep[0][0], keep[-1][0]))
    ns = [r[0] for r in keep]
    wall_a, wall_b = fit(ns, [r[1] for r in keep])
    print("wall 斜率 %.0f us/tok（截距 %.0f ms）\n" % (wall_a * 1000, wall_b))

    keys = set()
    for _, _, ph in keep:
        keys |= set(ph)
    out = []
    for k in keys:
        ys = [ph.get(k, 0) for _, _, ph in keep]
        a, b = fit(ns, ys)
        out.append((a * 1000, b, k, sum(ys) / len(ys)))
    out.sort(reverse=True)
    print("%-24s %10s %10s %10s" % ("相位", "us/tok", "占wall", "均值ms"))
    tot = 0.0
    for a, b, k, avg in out:
        if a <= 0:
            continue
        tot += a
        print("%-24s %10.0f %9.1f%% %10.0f" % (k, a, 100 * a / (wall_a * 1000), avg))
    print("%-24s %10.0f %9.1f%%" % ("== 正斜率之和 ==", tot, 100 * tot / (wall_a * 1000)))


if __name__ == "__main__":
    main()
