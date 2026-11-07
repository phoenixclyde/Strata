# -*- coding: utf-8 -*-
"""w861_time_weight.py -- 在 real_traffic 的分档基础上，算"时间加权"而不是"条数加权"。

为什么算这个：763 条短档占 14.2% 的请求，但"每 token 贵 9.5x"到底换算成多少**总时间**，
决定 R19 值不值得停服。条数占比会严重低估。

用法（166 上）：python3 w861_time_weight.py [/data/xxx.log] [since_line]
输出：按 prompt 桶的 条数 / read 总秒 / gen 总秒 / 各自占总时间比 / 每 token 成本
"""
from __future__ import annotations

import re
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else "/data/strata-huihui-ud-iq4_xs.log"
SINCE = int(sys.argv[2]) if len(sys.argv) > 2 else 0

RE_PREFILL = re.compile(
    r"strata serve: prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms "
    r"\(([\d.]+) tok/s\), (\d+) generated in (\d+) ms \(([\d.]+) tok/s\), "
    r"drafts accepted (\d+) of (\d+), (\d+) checkpoints"
)
# 短档请求的 PCIe / 专家行，用于审计"专家冷读"这个说法
RE_HIT = re.compile(
    r"decode expert cache hit rate: ([\d.]+)% \((\d+) hits / (\d+) lookups\); "
    r"(\d+) more read by the GPU over PCIe or from another GPU \(([\d.]+)% of all (\d+) routed\)"
)

BUCKETS = [(0, 128), (128, 256), (256, 512), (512, 1024), (1024, 4096),
           (4096, 16384), (16384, 65536), (65536, 10 ** 9)]


def bucket(t: int):
    for lo, hi in BUCKETS:
        if lo <= t < hi:
            return "%d-%d" % (lo, hi)
    return "?"


def main() -> int:
    agg: dict[str, dict] = {}
    total_read = 0
    total_gen = 0
    n = 0
    last_hit = None
    hit_by_bucket: dict[str, list] = {}

    with open(LOG, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, ln in enumerate(fh, 1):
            if lineno < SINCE:
                continue
            m = RE_HIT.search(ln)
            if m:
                last_hit = (float(m.group(1)), int(m.group(4)), float(m.group(5)))
                continue
            m = RE_PREFILL.search(ln)
            if not m:
                continue
            tok = int(m.group(1))
            read_tok = int(m.group(3))
            read_ms = int(m.group(4))
            gen_tok = int(m.group(6))
            gen_ms = int(m.group(7))
            acc_n = int(m.group(10))
            acc_d = int(m.group(11))
            b = bucket(tok)
            a = agg.setdefault(b, {"n": 0, "read": 0, "gen": 0, "rtok": 0, "gtok": 0,
                                   "acc_n": 0, "acc_d": 0})
            a["n"] += 1
            a["read"] += read_ms
            a["gen"] += gen_ms
            a["rtok"] += read_tok
            a["gtok"] += gen_tok
            a["acc_n"] += acc_n
            a["acc_d"] += acc_d
            total_read += read_ms
            total_gen += gen_ms
            n += 1
            if last_hit is not None:
                hit_by_bucket.setdefault(b, []).append(last_hit)
                last_hit = None

    print("requests=%d  total_read=%.1fs  total_gen=%.1fs  total=%.1fs"
          % (n, total_read / 1e3, total_gen / 1e3, (total_read + total_gen) / 1e3))
    print()
    hdr = ("bucket", "n", "n%", "read_s", "read%", "gen_s", "gen%", "tot%",
           "ms/1k_new", "read_tok", "read tok/s")
    print("%-12s %5s %6s %8s %7s %8s %7s %7s %10s %9s %9s"
          % hdr)
    for b in [x for x in ("%d-%d" % t for t in BUCKETS)]:
        a = agg.get(b)
        if not a or a["n"] == 0:
            continue
        rd = a["read"] / 1e3
        gn = a["gen"] / 1e3
        tot = rd + gn
        # 每 1k 新 token 的读入成本（与 real_traffic 同口径）
        ms1k = a["read"] / (a["rtok"] / 1000.0) if a["rtok"] else 0
        tps = a["rtok"] / (a["read"] / 1e3) if a["read"] else 0
        print("%-12s %5d %5.1f%% %8.1f %6.1f%% %8.1f %6.1f%% %6.1f%% %10.0f %9d %9.0f"
              % (b, a["n"], 100.0 * a["n"] / n, rd, 100.0 * rd / total_read,
                 gn, 100.0 * gn / total_gen, 100.0 * tot / (total_read + total_gen),
                 ms1k, a["rtok"], tps))
    print()
    print("=== 短档(<512) 合计 ===")
    for lim in (128, 512, 1024):
        nn = sum(a["n"] for b, a in agg.items()
                 if int(b.split("-")[0]) < lim)
        rr = sum(a["read"] for b, a in agg.items()
                 if int(b.split("-")[0]) < lim)
        gg = sum(a["gen"] for b, a in agg.items()
                 if int(b.split("-")[0]) < lim)
        tt = sum(a["read"] + a["gen"] for b, a in agg.items()
                 if int(b.split("-")[0]) < lim)
        print("  prompt<%d : n=%d (%.1f%% of reqs)  read=%.1fs (%.1f%%)  "
              "gen=%.1fs  total=%.1fs (%.1f%% of all time)"
              % (lim, nn, 100.0 * nn / n, rr / 1e3, 100.0 * rr / total_read,
                 gg / 1e3, tt / 1e3, 100.0 * tt / (total_read + total_gen)))
    print()
    print("=== 专家命中/PCIe 按桶（审计'专家冷读'） ===", )
    for b in [x for x in ("%d-%d" % t for t in BUCKETS)]:
        v = hit_by_bucket.get(b)
        if not v:
            continue
        h = sum(x[0] for x in v) / len(v)
        pc = sum(x[1] for x in v) / len(v)
        pcp = sum(x[2] for x in v) / len(v)
        print("  %-12s n=%4d  hit=%.1f%%  pcie_experts=%.1f  pcie%%=%.2f%%"
              % (b, len(v), h, pc, pcp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
