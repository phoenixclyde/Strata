#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W809 草稿策略扫描分析器。

口径（全部来自 DT 行的字段定义，见 generate.cpp:15050）：
  windows        dec_windows
  avg T          dec_T / windows     —— 每次校验的草稿行数（dec_T += merged ? 1 : T，15014 行）
  tokens/window  produced_n / windows
  ms/window      decode_ms / windows
  => **ms/token = ms/window ÷ tokens/window**，这是引擎内部测的，不含客户端开销（W808 的教训）
  另有 verify 内部拆分：GPU-reach wait / per-layer host / stage，以及 commit/emit 与 draft。

用法：python w809_analyze.py <driver.txt> [arm,...]
"""
import json
import re
import statistics as st
import sys

import os
D = os.path.dirname(os.path.abspath(sys.argv[1]))
# 逐个字段抽，不写一个大正则：括号里的字段数会随版本变（[plan actq jobs CPU] 是 8 个 token）
def _f(ln, pat, d=0.0):
    m = re.search(pat, ln)
    return float(m.group(1)) if m else d


def parse_dt(ln):
    return {
        "w": _f(ln, r"(\d+) windows"),
        "T": _f(ln, r"avg T ([0-9.]+)"),
        "tpw": _f(ln, r"([0-9.]+) tokens/window"),
        "mspw": _f(ln, r"([0-9.]+) ms/window"),
        "verify": _f(ln, r"verify ([0-9.]+)"),
        "gpu": _f(ln, r"GPU-reach wait ([0-9.]+)"),
        "host": _f(ln, r"per-layer host ([0-9.]+)"),
        "stage": _f(ln, r"\+ stage ([0-9.]+)"),
        "commit": _f(ln, r"commit/emit ([0-9.]+)"),
        "draft": _f(ln, r"draft ([0-9.]+);"),
    }


DA = re.compile(r"drafts accepted (\d+) of (\d+)")


def load(path):
    arms, cur = {}, None
    for ln in open(path, encoding="utf-8", errors="replace"):
        m = re.search(r"^=== ARM (\w+) spec=([\d.]+) min_p=([\d.]+)", ln)
        if m:
            cur = m.group(1)
            arms[cur] = {"spec": m.group(2), "minp": m.group(3), "dt": [], "da": []}
            continue
        if cur is None:
            continue
        if "strata decode timing:" in ln and "ms/window" in ln:
            arms[cur]["dt"].append(parse_dt(ln))
            continue
        m = DA.search(ln)
        if m and "  DA " in ln:
            arms[cur]["da"].append((int(m.group(1)), int(m.group(2))))
    return arms


def med(rows, k):
    return st.median([r[k] for r in rows])


def main():
    path = sys.argv[1]
    keep = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] not in ("", "-") else None
    drop = int(sys.argv[3]) if len(sys.argv) > 3 else 0   # 每臂丢掉前 drop 条（重启后前两个请求是冷的，P98）
    arms = load(path)
    if drop:
        for a in arms:
            arms[a]["dt"] = arms[a]["dt"][drop:]
    order = [a for a in arms if (keep is None or a in keep)]
    print("%-4s %-6s %-6s | %-7s %-7s %-8s %-8s | %-7s %-7s %-7s %-7s | %-6s %-6s"
          % ("arm", "spec", "min_p", "avg T", "tok/win", "ms/win", "**ms/tok**",
             "GPU", "host", "draft", "commit", "accept", "acc%"))
    base = None
    for a in order:
        r = arms[a]["dt"]
        if not r:
            print("%-4s %-6s %-6s | (no DT rows)" % (a, arms[a]["spec"], arms[a]["minp"]))
            continue
        mspw, tpw = med(r, "mspw"), med(r, "tpw")
        mstok = st.median([x["mspw"] / x["tpw"] for x in r])
        acc = arms[a]["da"]
        accn = sum(x[0] for x in acc)
        accd = sum(x[1] for x in acc)
        print("%-4s %-6s %-6s | %-7.2f %-7.2f %-8.2f %-8.2f | %-7.2f %-7.2f %-7.2f %-7.2f | %-6s %-6s"
              % (a, arms[a]["spec"], arms[a]["minp"], med(r, "T"), tpw, mspw, mstok,
                 med(r, "gpu"), med(r, "host"), med(r, "draft"), med(r, "commit"),
                 "%d/%d" % (accn, accd) if accd else "-",
                 "%.1f" % (100.0 * accn / accd) if accd else "-"))
        if a == order[0]:
            base = mstok
    if base:
        print("\n相对 %s 的 ms/token（负 = 更快）:" % order[0])
        for a in order[1:]:
            r = arms[a]["dt"]
            if not r:
                continue
            mstok = st.median([x["mspw"] / x["tpw"] for x in r])
            per = ["%.1f" % (x["mspw"] / x["tpw"]) for x in r]
            print("  %-4s %+6.1f%%  逐条 ms/tok = %s" % (a, 100 * (mstok - base) / base, " / ".join(per)))
    # decode_tps 交叉核对（服务端 /metrics，不含客户端）
    print("\n服务端 decode tok/s（交叉核对）:")
    for a in order:
        try:
            d = json.load(open("%s/w809_gen_%s.json" % (D, a), encoding="utf-8"))
            v = [x["decode_tps"] for x in d["results"] if x.get("decode_tps")]
            if v:
                print("  %-4s %-28s 中位 %.2f" % (a, " ".join("%.1f" % x for x in v), st.median(v)))
        except Exception as e:
            print("  %-4s (json 缺: %s)" % (a, str(e)[:40]))


if __name__ == "__main__":
    main()
