#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 engine-start 切段：每次启动 = 一种配置，汇总 prefill 分档 + decode 窗口速率。"""
import re, statistics, datetime, io, os

LOG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log"

r_start = re.compile(r"^\[strata\] (2026-\d\d-\d\d \d\d:\d\d:\d\d) engine started: (\S+)")
r_pref = re.compile(r"prompt (\d+) tokens = .*? \((\d+\.\d+) tok/s\), (\d+) generated in (\d+) ms \((\d+\.\d+) tok/s\)")
r_win = re.compile(r"decode timing: \d+ windows, avg T [\d.]+, ([\d.]+) tokens/window, ([\d.]+) ms/window")

runs = []
cur = None
for line in io.open(LOG, encoding="utf-8", errors="replace"):
    m = r_start.match(line)
    if m:
        ts = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S") + datetime.timedelta(hours=8)
        cur = {"ts": ts, "exe": os.path.basename(m.group(2)), "pref": [], "win": [], "gen": []}
        runs.append(cur)
        continue
    if cur is None:
        continue
    m = r_pref.search(line)
    if m:
        cur["pref"].append((int(m.group(1)), float(m.group(2))))
        if int(m.group(3)) >= 4:
            cur["gen"].append(float(m.group(5)))
        continue
    m = r_win.search(line)
    if m:
        tk, ms = float(m.group(1)), float(m.group(2))
        if ms > 0:
            cur["win"].append((tk, ms))

def band(rows, lo, hi):
    xs = [p for n, p in rows if lo <= n < hi]
    return statistics.median(xs) if xs else None

def f(x, w=6, p=1):
    return ("%" + str(w) + "." + str(p) + "f") % x if x is not None else "-".rjust(w)

print("CST start            exe                 n_pref  p2K   p8K   p16K  p32K  p60K  p130K  dec_win  ms/win  dec_req")
for r in runs:
    if r["ts"] < datetime.datetime(2026, 11, 3):
        continue
    n = len(r["pref"])
    if n == 0 and not r["win"]:
        continue
    w = r["win"]
    tk = statistics.median([x[0] for x in w]) if w else None
    ms = statistics.median([x[1] for x in w]) if w else None
    dec = (tk / (ms / 1000.0)) if (tk and ms) else None
    req = statistics.median(r["gen"]) if r["gen"] else None
    print("%s  %-18s %6d %s %s %s %s %s %s %s %s %s" % (
        r["ts"].strftime("%m-%d %H:%M"), r["exe"][:18], n,
        f(band(r["pref"], 1500, 3000)), f(band(r["pref"], 7000, 9000)),
        f(band(r["pref"], 14000, 17500)), f(band(r["pref"], 30000, 34000)),
        f(band(r["pref"], 55000, 65000)), f(band(r["pref"], 100000, 200000)),
        f(dec), f(ms, 6, 2), f(req)))
