# -*- coding: utf-8 -*-
"""W804 分析：read 长扫描（A=auto/MAX1024, B=auto/MAX3072, C=share 0, D=0+STREAM_MIN3072, E=auto/MAX4096）

数据源 = 驱动器的 .txt（`LOG strata serve: prompt N tokens = R reused + F read in T ms (K tok/s)` 与
`PH strata prefill timing: ...`）。判读用**实测 prompt_tokens** 分档，不用目标尺寸。

输出：
  1) 每个 read 档的 read 时间（中位）与各臂相对 C 的差；
  2) 最大两档的相位账（W800 那张图已过期）。
"""
import re, statistics as st, sys

P = sys.argv[1]
lines = open(P, encoding="utf-8", errors="replace").read().split("\n")
arms, cur = {}, None
for ln in lines:
    m = re.match(r"=== ARM (\w)", ln)
    if m:
        cur = m.group(1)
        arms[cur] = {"req": [], "ph": []}
        continue
    if cur is None:
        continue
    m = re.search(r"prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms \(([\d.]+) tok/s\)", ln)
    if m:
        arms[cur]["req"].append((int(m.group(1)), int(m.group(3)), int(m.group(4)), float(m.group(5))))
        continue
    m = re.search(r"prefill timing: (\d+) tokens, GPU timeline (\d+) ms, wall (\d+) ms, host staging (\d+) ms:(.*)$", ln)
    if m:
        ph = {}
        for x in re.finditer(r"([A-Za-z][A-Za-z0-9 +:/().\-]*?)\s+(\d+) \((\d+\.\d)%\)", m.group(5)):
            ph[x.group(1).strip()] = (int(x.group(2)), float(x.group(3)))
        arms[cur]["ph"].append((int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), ph))

ARMS = sorted(arms)
print("== 每臂的请求（read = 实际读取 token）==")
for a in ARMS:
    d = arms[a]
    print("  ARM %-2s n=%-3d %s" % (a, len(d["req"]), [r[1] for r in d["req"]]))


def bucket(n):
    return int(round(n / 100.0)) * 100


rows = {}
for a in ARMS:
    for tot, read, ms, tps in arms[a]["req"]:
        rows.setdefault(bucket(read), {}).setdefault(a, []).append((read, ms, tps))

print("")
print("== read 分档：中位 read / 中位 ms / 中位 tok/s，差相对 C（share 0）==")
print("%-7s" % "read" + "".join(" | %-26s" % ("ARM " + a) for a in ARMS))
for b in sorted(rows):
    base = rows[b].get("C")
    base_ms = st.median([x[1] for x in base]) if base else None
    line = "%-7d" % b
    for a in ARMS:
        v = rows[b].get(a)
        if not v:
            line += " | %-26s" % "-"
            continue
        ms = st.median([x[1] for x in v])
        tps = st.median([x[2] for x in v])
        dd = ("%+.1f%%" % (100.0 * (ms - base_ms) / base_ms)) if base_ms else "  n/a"
        line += " | %5d %6.0fms %5.0ft/s %s" % (st.median([x[0] for x in v]), ms, tps, dd)
    print(line)

print("")
print("== 相位账（最大两档，每个 chunk 的中位百分比）==")
for b in sorted(rows)[-2:]:
    print("  --- read 档 %d ---" % b)
    for a in ARMS:
        ps = [p for p in arms[a]["ph"] if bucket(p[0]) == b]
        if not ps:
            print("    ARM %s (无相位行)" % a)
            continue
        acc = {}
        for _, _, _, _, ph in ps:
            for k, v in ph.items():
                acc.setdefault(k, []).append(v[1])
        top = sorted(acc.items(), key=lambda kv: -st.median(kv[1]))[:8]
        print("    ARM %s n=%d timeline %d ms :: %s"
              % (a, len(ps), st.median([p[1] for p in ps]),
                 " · ".join("%s %.0f%%" % (k, st.median(v)) for k, v in top)))
