#!/usr/bin/env python3
# W1051 parse: gdn phase A/B + decode tok/s + G2 numeric verdict from phase_g2.txt / pcompare_g2.txt
import io
import re
import statistics

W = r"D:/workbuddy_space/strata_ws/albus/w1051"


def stat(v):
    if not v:
        return "-"
    m = statistics.mean(v)
    cv = (statistics.pstdev(v) / m * 100) if len(v) > 1 and m else 0.0
    return "n=%d mean=%.1f cv=%.2f%% vals=%s" % (len(v), m, cv, v)


def phases():
    rows = {}
    try:
        txt = io.open(W + "/phase_g2.txt", encoding="utf-8", errors="replace").read()
    except FileNotFoundError:
        print("(phase_g2 missing)")
        return rows
    for line in txt.splitlines():
        m = re.match(r"(P2K5|P8K|DEC) (\S+) (r\d+) (.*)", line.strip())
        if not m:
            continue
        kind, arm, rep, rest = m.groups()
        d = rows.setdefault((arm, kind), {"gpu": [], "gdn": [], "tps": [], "toks": []})
        if "MISSING" in rest:
            d.setdefault("missing", []).append(rest)
            continue
        if kind == "DEC":
            g = re.search(r"(\d+) generated in (\d+) ms \(([0-9.]+) tok/s\)", rest)
            if g:
                d["toks"].append(int(g.group(1)))
                d["tps"].append(float(g.group(3)))
        else:
            g = re.search(r"(\d+) tokens, GPU timeline (\d+) ms", rest)
            if g:
                d["toks"].append(int(g.group(1)))
                d["gpu"].append(int(g.group(2)))
            g = re.search(r"\bgdn (\d+) \(", rest)
            if g:
                d["gdn"].append(int(g.group(1)))
    print("== phase table ==")
    for arm in ("a_off", "b_on"):
        for kind in ("P2K5", "P8K", "DEC"):
            d = rows.get((arm, kind))
            if not d:
                continue
            if kind == "DEC":
                print("%-6s %-4s tps=%s toks=%s missing=%s" % (
                    arm, kind, stat(d["tps"]), stat(d["toks"]), d.get("missing")))
            else:
                print("%-6s %-4s gpu=%s gdn=%s missing=%s" % (
                    arm, kind, stat(d["gpu"]), stat(d["gdn"]), d.get("missing")))
    print("== deltas (b_on vs a_off) ==")
    for kind in ("P2K5", "P8K"):
        a = rows.get(("a_off", kind), {})
        b = rows.get(("b_on", kind), {})
        if a.get("gdn") and b.get("gdn"):
            ma, mb = statistics.mean(a["gdn"]), statistics.mean(b["gdn"])
            ga, gb = statistics.mean(a["gpu"]), statistics.mean(b["gpu"])
            print("%-4s gdn %.0f -> %.0f (%+.2f%%) | gpu %.0f -> %.0f (%+.2f%%)" % (
                kind, ma, mb, (mb - ma) / ma * 100, ga, gb, (gb - ga) / ga * 100))
    a = rows.get(("a_off", "DEC"), {})
    b = rows.get(("b_on", "DEC"), {})
    if a.get("tps") and b.get("tps"):
        ta, tb = statistics.mean(a["tps"]), statistics.mean(b["tps"])
        print("DEC tps %.1f -> %.1f (%+.2f%%)" % (ta, tb, (tb - ta) / ta * 100))
    return rows


def pcomps():
    print("== pcompare ==")
    try:
        txt = io.open(W + "/pcompare_g2.txt", encoding="utf-8", errors="replace").read()
    except FileNotFoundError:
        print("(pcompare missing)")
        return
    for line in txt.splitlines():
        m = re.search(r"CMP (\S+) vs (\S+) L_\S+\s+prompts\s+(\d+)\s+top-1\s+([0-9.]+)%\s+KL mean ([0-9.]+)\s+median ([0-9.]+)\s+max ([0-9.]+)", line)
        if m:
            ref, run, np_, top1, klm, klmed, klmax = m.groups()
            print("ref=%-3s run=%-3s prompts=%s top-1=%s%% KL mean=%s median=%s max=%s" % (
                ref, run, np_, top1, klm, klmed, klmax))


if __name__ == "__main__":
    phases()
    pcomps()
