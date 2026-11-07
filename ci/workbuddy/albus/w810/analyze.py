# -*- coding: utf-8 -*-
"""W810 / P138 分析器：从 ab_p40.sh 的 OUT 文本里做表。

规则对账：
  Z  —— 相位表加总必须 == GPU timeline（误差 <=1%），且 >=2% 的项全列；
  T  —— 每个百分比都带分母（分母 = GPU timeline / 请求数）；
  S  —— 列名绑来源：PL(客户端真值行) / PH(GPU 相位表) / PHH(主机累计) / DT(解码结构) / MEDIAN(metrics)。
  X  —— 同配置两遍（A vs A2）先看噪声地板。
"""
import re
import sys
from collections import OrderedDict, defaultdict

OUT = sys.argv[1] if len(sys.argv) > 1 else "w810_pleio.txt"
lines = open(OUT, encoding="utf-8", errors="replace").read().splitlines()

RE_ARM = re.compile(r"^=== ARM (\S+).*ready=(\d+)s.*start_wall=(\d+)s")
RE_PL = re.compile(r"prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms \(([\d.]+) tok/s\)")
RE_PH = re.compile(r"^  PH strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms, wall (\d+) ms, host staging (\d+) ms: (.*)$")
RE_PHH = re.compile(r"^  PHH .*PLE (\d+) ms")
RE_MED = re.compile(r"MEDIAN decode_tps = ([\d.]+)")
RE_DT = re.compile(r"^  DT strata decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window")

arms = OrderedDict()
cur = None
for ln in lines:
    m = RE_ARM.match(ln)
    if m:
        cur = {"name": m.group(1), "ready": int(m.group(2)), "wall": int(m.group(3)),
               "pl": [], "ph": [], "phh": [], "med": None, "dt": []}
        arms[cur["name"]] = cur
        continue
    if cur is None:
        continue
    m = RE_PL.search(ln)
    if m:
        cur["pl"].append(dict(tok=int(m.group(1)), reused=int(m.group(2)), read_ms=int(m.group(4)), tps=float(m.group(5))))
        continue
    m = RE_PH.search(ln)
    if m:
        body = m.group(5)
        pairs = re.findall(r"([a-z][a-z /+]*?) (\d+) \(([\d.]+)%\)", body)
        cur["ph"].append(dict(tok=int(m.group(1)), total=int(m.group(2)), staging=int(m.group(4)),
                              parts=[(n.strip(), int(v), float(p)) for n, v, p in pairs]))
        continue
    m = RE_PHH.search(ln)
    if m:
        cur["phh"].append(int(m.group(1)))
        continue
    m = RE_MED.search(ln)
    if m:
        cur["med"] = float(m.group(1))
        continue
    m = RE_DT.match(ln)
    if m:
        cur["dt"].append(dict(w=int(m.group(1)), T=float(m.group(2)), tpw=float(m.group(3)), msw=float(m.group(4))))

print("=" * 118)
print("W810 / P138 —— 提示侧 PLE 通道   （GPU timeline 分母；PL 为引擎真值行，客户端只做交叉检查）")
print("=" * 118)

hdr = "%-6s %-4s %7s %9s %8s %9s %8s %8s %8s %7s" % (
    "arm", "idx", "tokens", "read_ms", "tok/s", "timeline", "ple_ms", "ple%", "phH_ms", "dec_tps")
print(hdr)
print("-" * len(hdr))

for name, a in arms.items():
    phh_delta = []
    run = 0
    for v in a["phh"]:
        phh_delta.append(v - run)
        run = v
    for i, r in enumerate(a["pl"]):
        ph = a["ph"][i] if i < len(a["ph"]) else None
        ple = next((v for n, v, p in ph["parts"] if n == "ple"), None) if ph else None
        pct = next((p for n, v, p in ph["parts"] if n == "ple"), None) if ph else None
        hh = phh_delta[i] if i < len(phh_delta) else None
        print("%-6s %-4d %7d %9d %8.1f %9s %8s %8s %8s %7s" % (
            name, i, r["tok"], r["read_ms"], r["tps"],
            ph["total"] if ph else "-", ple if ple is not None else "-",
            ("%.1f" % pct) if pct is not None else "-",
            hh if hh is not None else "-",
            ("%.1f" % a["med"]) if a["med"] and i == 0 else ""))
    # 规则 Z：相位表加总
    for i, ph in enumerate(a["ph"]):
        s = sum(v for n, v, p in ph["parts"])
        d = 100.0 * (ph["total"] - s) / ph["total"]
        if abs(d) > 1.0:
            print("  !! Z-VIOLATION arm=%s req=%d 加总=%d timeline=%d 差=%.1f%%"
                  % (name, i, s, ph["total"], d))
    print()

print("-" * 118)
print("按 tokens 归一（每 1k token 的 ms）：")
print("%-6s %8s %10s %10s %10s %10s" % ("arm", "tokens", "read/1k", "ple/1k", "phH/1k", "ple_share"))
for name, a in arms.items():
    phh_delta, run = [], 0
    for v in a["phh"]:
        phh_delta.append(v - run)
        run = v
    for i, r in enumerate(a["pl"]):
        if i >= len(a["ph"]):
            break
        ph = a["ph"][i]
        ple = next((v for n, v, p in ph["parts"] if n == "ple"), 0)
        hh = phh_delta[i] if i < len(phh_delta) else 0
        k = r["tok"] / 1000.0
        print("%-6s %8d %10.1f %10.1f %10.1f %9.1f%%" % (
            name, r["tok"], r["read_ms"] / k, ple / k, hh / k, 100.0 * ple / ph["total"]))
