#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT10 · W809 独立重算（不引用 w809_analyze.py / 文档）。

从原始驱动件的 DT 行逐字段重算：
  avg T / tokens/window / ms/window = verify(...) + commit/emit + draft
  ms/token = ms/window ÷ tokens/window
每臂：全部 6 条、丢掉前 drop 条（冷启）、以及「中位 / 逐条」。
同时核对 VW（引擎命令行）与 FUSECHECK 是否与臂声明一致。
"""
import re
import statistics as st
import sys

F = re.compile


def parse(path):
    arms, cur = {}, None
    for ln in open(path, encoding="utf-8", errors="replace"):
        m = F(r"^=== ARM (\S+) spec=([\d.]+) min_p=([\d.]+)(?: nenv=(\d+))?").search(ln)
        if m:
            cur = m.group(1)
            arms[cur] = {"spec": m.group(2), "minp": m.group(3), "nenv": m.group(4),
                         "dt": [], "vw": None, "fuse": None, "pool": None, "med": None}
            continue
        if cur is None:
            continue
        a = arms[cur]
        if re.match(r"^\s+VW ", ln):
            a["vw"] = ln.strip()[3:]
        elif "FUSECHECK" in ln:
            m = F(r"engine_env_hits=(\d+)").search(ln)
            a["fuse"] = int(m.group(1)) if m else None
        elif re.match(r"^\s+POOL ", ln):
            m = F(r"slots=(\d+) vram=(\d+)").search(ln)
            if m:
                a["pool"] = (int(m.group(1)), int(m.group(2)))
        elif "MEDIAN decode_tps" in ln:
            m = F(r"MEDIAN decode_tps = ([\d.]+)").search(ln)
            if m:
                a["med"] = float(m.group(1))
        elif "strata decode timing:" in ln and "ms/window" in ln:
            g = lambda p, d=0.0: float(F(p).search(ln).group(1)) if F(p).search(ln) else d
            a["dt"].append({
                "T": g(r"avg T ([\d.]+)"),
                "tpw": g(r"([\d.]+) tokens/window"),
                "mspw": g(r"([\d.]+) ms/window"),
                "gpu": g(r"GPU-reach wait ([\d.]+)"),
                "host": g(r"per-layer host ([\d.]+)"),
                "draft": g(r"draft ([\d.]+);"),
                "commit": g(r"commit/emit ([\d.]+)"),
            })
    return arms


def table(path, drop, label):
    arms = parse(path)
    print("\n== %s  (drop first %d of %d DT rows)" % (label, drop, len(next(iter(arms.values()))["dt"]) if arms else 0))
    print("%-5s %-6s %-6s %-6s | %-6s %-7s %-7s %-8s | %-6s %-6s %-6s | %-5s %-6s"
          % ("arm", "spec", "minp", "nenv", "n", "avg T", "tok/w", "ms/tok",
             "gpu", "host", "draft", "fuse", "slots"))
    base = None
    rows = {}
    for a, d in arms.items():
        xs = d["dt"][drop:]
        if not xs:
            print("%-5s (no DT)" % a)
            continue
        mstok = [x["mspw"] / x["tpw"] for x in xs]
        row = dict(n=len(xs), T=st.median([x["T"] for x in xs]), tpw=st.median([x["tpw"] for x in xs]),
                   mstok=st.median(mstok), gpu=st.median([x["gpu"] for x in xs]),
                   host=st.median([x["host"] for x in xs]), draft=st.median([x["draft"] for x in xs]))
        rows[a] = row
        if base is None:
            base = row["mstok"]
        print("%-5s %-6s %-6s %-6s | %-6d %-7.2f %-7.2f %-8.2f | %-6.2f %-6.2f %-6.2f | %-5s %-6s"
              % (a, d["spec"], d["minp"], d["nenv"] or "-", row["n"], row["T"], row["tpw"], row["mstok"],
                 row["gpu"], row["host"], row["draft"],
                 d["fuse"] if d["fuse"] is not None else "-",
                 d["pool"][0] if d["pool"] else "-"))
    print("  逐条 ms/token:")
    for a, d in arms.items():
        xs = d["dt"][drop:]
        print("    %-5s %s" % (a, " ".join("%.1f" % (x["mspw"] / x["tpw"]) for x in xs)))
    print("  相对首臂:")
    for a, r in rows.items():
        if a == list(rows)[0]:
            continue
        print("    %-5s %+6.1f%%" % (a, 100 * (r["mstok"] - base) / base))
    print("  VW / fuse 自证:")
    for a, d in arms.items():
        print("    %-5s vw='%s' fuse=%s" % (a, d["vw"], d["fuse"]))


if __name__ == "__main__":
    table("albus/audit10/w809_spec_20261026_220550.txt", 1, "W809a spec/min_p (3 prompt/arm, drop 1)")
    table("albus/audit10/w809b_fuse_20261026_221847.txt", 2, "W809b fusion stack (6 prompt/arm)")
    table("albus/audit10/w809c_b6_20261026_222959.txt", 2, "W809c B6/GU_SWIGLU (6 prompt/arm)")
