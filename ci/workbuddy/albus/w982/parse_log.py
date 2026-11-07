#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按日期汇总生产日志里的 prefill / decode / 窗口耗时。"""
import re, statistics, collections, io

LOG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log"
date = None
pref = collections.defaultdict(list)     # date -> [(n, tok_s)]
dec_req = collections.defaultdict(list)  # date -> [tok_s]  (request-level, 4 tokens)
win = collections.defaultdict(list)      # date -> [ms/window, tokens/window]

re_date = re.compile(r"^\[strata\] (2026-\d\d-\d\d) (\d\d:\d\d)")
re_pref = re.compile(r"prompt (\d+) tokens = .* \((\d+\.\d+) tok/s\), (\d+) generated in (\d+) ms \((\d+\.\d+) tok/s\)")
re_win = re.compile(r"decode timing: \d+ windows, avg T [\d.]+, ([\d.]+) tokens/window, ([\d.]+) ms/window")

for line in io.open(LOG, encoding="utf-8", errors="replace"):
    m = re_date.match(line)
    if m:
        date = m.group(1) + " " + m.group(2)
        continue
    if date is None:
        continue
    m = re_pref.search(line)
    if m:
        n = int(m.group(1)); p = float(m.group(2))
        gen = int(m.group(3)); dwin = float(m.group(5))
        pref[date].append((n, p))
        if gen >= 4:
            dec_req[date].append(dwin)
    m = re_win.search(line)
    if m:
        win[date].append((float(m.group(1)), float(m.group(2))))

print("%-17s %6s %10s %10s %10s %10s %10s" %
      ("date(CST)", "pref#", "p@2K", "p@8K", "p@16K", "p@60K", "p@130K"))
for d in sorted(pref):
    rows = pref[d]
    def band(lo, hi):
        xs = [p for n, p in rows if lo <= n < hi]
        return "%.1f" % statistics.median(xs) if xs else "-"
    print("%-17s %6d %10s %10s %10s %10s %10s" %
          (d, len(rows), band(1500, 3000), band(7000, 9000), band(14000, 17500),
           band(55000, 65000), band(100000, 200000)))

print()
print("%-17s %8s %8s   %s" % ("date(CST)", "win_ms", "tok/s", "n"))
for d in sorted(win):
    ms = [x[0] for x in win[d] if x[0] > 0]
    tk = [x[1] / (x[0] / 1000.0) for x in win[d] if x[0] > 0]
    if ms:
        print("%-17s %8.2f %8.2f   %d" % (d, statistics.median(ms), statistics.median(tk), len(ms)))

print()
print("%-17s %8s %8s   %s" % ("date(CST)", "req_t/s", "n", "（请求级 4-token decode）"))
for d in sorted(dec_req):
    if dec_req[d]:
        print("%-17s %8.2f %8d" % (d, statistics.median(dec_req[d]), len(dec_req[d])))
