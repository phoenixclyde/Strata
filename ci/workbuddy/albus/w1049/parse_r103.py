#!/usr/bin/env python3
# W1049: parse window_r103 outputs -> per-arm phase table + pcompare verdicts.
import io
import re
import sys

W = r"D:/workbuddy_space/strata_ws/albus/w1049"
PH = W + "/phase_summary.txt"
PC = W + "/pcompare_summary.txt"


def phases():
    rows = {}
    for line in io.open(PH, encoding="utf-8", errors="replace"):
        m = re.match(r"(PHASE2K5|PHASE8K|DECODE) (\S+) (.*)", line.strip())
        if not m:
            continue
        kind, arm, rest = m.groups()
        d = rows.setdefault((arm, kind), {})
        if kind == "DECODE":
            g = re.search(r"(\d+) generated in (\d+) ms \(([0-9.]+) tok/s\)", rest)
            if g:
                d["gen"] = int(g.group(1)); d["ms"] = int(g.group(2)); d["tps"] = float(g.group(3))
        else:
            g = re.search(r"(\d+) tokens, GPU timeline (\d+) ms", rest)
            if g:
                d.setdefault("gpu", []).append(int(g.group(2)))
                d.setdefault("tok", []).append(int(g.group(1)))
            for ph in ("qsa attn", "router\\+shared", "gather", "hc read: down\\+silu"):
                g = re.search(ph + r" (\d+) \(([0-9.]+)%\)", rest)
                if g:
                    key = ph.replace("\\", "")
                    d.setdefault(key, []).append(int(g.group(1)))
    print("arm kind tokens gpu_ms qsa_attn router_shared gather")
    for (arm, kind), d in sorted(rows.items()):
        if kind == "DECODE":
            print("%-9s DECODE tps=%.2f gen=%d ms=%d" % (arm, d.get("tps", 0), d.get("gen", 0), d.get("ms", 0)))
        else:
            gpu = d.get("gpu") or [0]
            tok = d.get("tok") or [0]
            qa = d.get("qsa attn") or [0]
            rs = d.get("router+shared") or [0]
            ga = d.get("gather") or [0]
            print("%-9s %-6s tok=%s gpu=%s qsa=%s router=%s gather=%s" %
                  (arm, kind, tok, gpu, qa, rs, ga))


def pcomps():
    print("\n=== pcompare_summary ===")
    try:
        txt = io.open(PC, encoding="utf-8", errors="replace").read()
    except FileNotFoundError:
        print("(missing)")
        return
    for line in txt.splitlines():
        if any(k in line.lower() for k in ("differ", "kl", "top", "cmp", "rel_rms", "identical")):
            print(line[:160])


def phases_b():
    import statistics
    try:
        txt = io.open(r"D:/workbuddy_space/strata_ws/albus/w1049/phase_b.txt", encoding="utf-8", errors="replace").read()
    except FileNotFoundError:
        print("(phase_b missing)")
        return
    rows = {}
    for line in txt.splitlines():
        m = re.match(r"(P2K5|P8K|DEC) (\S+) r?(\S*) (.*)", line.strip())
        if not m:
            continue
        kind, arm, rep, rest = m.groups()
        d = rows.setdefault((arm, kind), {"gpu": [], "qsa": [], "router": [], "gath": [], "tps": []})
        if kind == "DEC":
            g = re.search(r"(\d+) generated in (\d+) ms \(([0-9.]+) tok/s\)", rest)
            if g:
                d["tps"].append(float(g.group(3)))
        else:
            g = re.search(r"(\d+) tokens, GPU timeline (\d+) ms", rest)
            if g:
                d["gpu"].append(int(g.group(2)))
            for key, pat in (("qsa", r"qsa attn (\d+) "), ("router", r"router\+shared (\d+) "),
                             ("gath", r"gather (\d+) ")):
                g = re.search(pat, rest)
                if g:
                    d[key].append(int(g.group(1)))
    def stat(v):
        if not v:
            return "-"
        m = statistics.mean(v)
        cv = (statistics.pstdev(v) / m * 100) if len(v) > 1 and m else 0.0
        return "%.0f(cv%.1f%%)" % (m, cv)
    print("arm kind gpu qsa_attn router gather tps")
    order = ["a_floor", "b_dpp", "c_ldspad", "d_red12", "e_dp4a", "f_r103x", "g_route", "h_gather", "k_ilp"]
    for arm in order:
        for kind in ("P2K5", "P8K", "DEC"):
            d = rows.get((arm, kind))
            if not d:
                continue
            if kind == "DEC":
                print("%-9s %-4s tps=%s" % (arm, kind, stat(d["tps"])))
            else:
                print("%-9s %-4s gpu=%s qsa=%s router=%s gather=%s" %
                      (arm, kind, stat(d["gpu"]), stat(d["qsa"]), stat(d["router"]), stat(d["gath"])))


if __name__ == '__main__':
    phases()
    phases_b()
    pcomps()
