# -*- coding: utf-8 -*-
"""real_traffic.py -- 从生产引擎日志里抽"真实用户流量"画像（只读，零干扰）。

为什么要它：机主在用模型时的请求，是**非构造的真实负载**，比 mt_read.py 的合成探针
更能代表"哪里慢"。而且全程只读 /data/*.log，不碰 GPU、不重启、不停服。

用法（在 166 上跑）：python3 real_traffic.py [/data/strata-huihui-ud-iq4_xs.log]
输出：每次请求一行 + 按 prompt 长度分档的汇总 + 累计计数器。
"""
from __future__ import annotations

import re
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else "/data/strata-huihui-ud-iq4_xs.log"
SINCE = int(sys.argv[2]) if len(sys.argv) > 2 else 0  # 从第 N 行之后开始算（区分"本次启动"与"长期"）

RE_PREFILL = re.compile(
    r"strata serve: prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms "
    r"\(([\d.]+) tok/s\), (\d+) generated in (\d+) ms \(([\d.]+) tok/s\), "
    r"drafts accepted (\d+) of (\d+), (\d+) checkpoints"
)
RE_HIT = re.compile(
    r"strata serve: decode expert cache hit rate: ([\d.]+)% \((\d+) hits / (\d+) lookups\); "
    r"(\d+) more read by the GPU over PCIe or from another GPU \(([\d.]+)% of all (\d+) routed\)"
)
RE_TAIL = re.compile(r"strata serve: route tail skip: (\d+) missed experts skipped \((\d+) entries\)")
RE_PARK = re.compile(
    r"strata serve: conversation cache: parked (\d+) tokens in ([\d.]+) ms; parked=(\d+) "
    r"bytes=(\d+) evictions=(\d+)"
)
RE_SUFFIX = re.compile(r"strata serve: suffix drafts: (\d+) windows, (\d+) of (\d+) drafts accepted")


def main() -> int:
    reqs: list[dict] = []
    cur: dict | None = None
    tail_skip = tail_entries = 0
    parks: list[tuple[int, float]] = []
    suffix: list[tuple[int, int]] = []

    with open(LOG, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, ln in enumerate(fh, 1):
            if lineno < SINCE:
                continue
            m = RE_PREFILL.search(ln)
            if m:
                g = [int(x) for x in m.group(1, 2, 3, 4, 6, 7)]
                cur = {
                    "tok": g[0], "reused": g[1], "read_tok": g[2],
                    "read_ms": g[3], "gen": g[4], "gen_ms": g[5],
                    "read_tps": float(m.group(5)), "gen_tps": float(m.group(8)),
                    "draft_ok": int(m.group(9)), "draft_all": int(m.group(10)),
                    "ckpt": int(m.group(11)),
                }
                reqs.append(cur)
                continue
            m = RE_HIT.search(ln)
            if m and reqs:
                cur["hit"] = float(m.group(1))
                cur["routed"] = int(m.group(6))
                cur["pcie_pct"] = float(m.group(5))
                continue
            m = RE_TAIL.search(ln)
            if m:
                tail_skip, tail_entries = int(m.group(1)), int(m.group(2))
                continue
            m = RE_PARK.search(ln)
            if m:
                parks.append((int(m.group(1)), float(m.group(2))))
                continue
            m = RE_SUFFIX.search(ln)
            if m:
                suffix.append((int(m.group(2)), int(m.group(3))))

    print("=" * 96)
    print("真实流量：%d 条请求%s" % (len(reqs), ("（自第 %d 行起）" % SINCE) if SINCE else "（全量，跨多次启动）"))
    print("=" * 96)
    hdr = ("#", "prompt", "reused", "read_ms", "read_t/s", "gen", "gen_ms", "gen_t/s", "MTP%", "hit%", "PCIe%")
    print(("%-3s %8s %8s %8s %9s %6s %8s %9s %6s %6s %6s") % hdr)
    for i, r in enumerate(reqs, 1):
        mtp = 100.0 * r["draft_ok"] / r["draft_all"] if r["draft_all"] else float("nan")
        print(("%-3d %8d %8d %8d %9.1f %6d %8d %9.1f %6.1f %6s %6s") % (
            i, r["tok"], r["reused"], r["read_ms"], r["read_tps"],
            r["gen"], r["gen_ms"], r["gen_tps"], mtp,
            ("%.1f" % r["hit"]) if "hit" in r else "-",
            ("%.1f" % r["pcie_pct"]) if "pcie_pct" in r else "-",
        ))

    # 分档
    bands = [(0, 128), (128, 1024), (1024, 4096), (4096, 16384), (16384, 10 ** 9)]
    print()
    print("按 prompt 长度分档（只统计真的读了 >0 token 的请求）")
    print("%-16s %5s %11s %10s %9s %9s %8s %8s" % ("band", "n", "ms/1k_new", "read_t/s", "gen_t/s", "MTP%", "hit%", "PCIe%"))
    for lo, hi in bands:
        sel = [r for r in reqs if lo <= r["tok"] < hi and r["read_tok"] > 0]
        if not sel:
            continue
        rd = sum(r["read_tok"] for r in sel)
        per_k = sum(r["read_ms"] for r in sel) / rd * 1000 if rd else 0.0
        rt = sum(r["read_tok"] for r in sel) / sum(r["read_ms"] for r in sel) * 1000
        gt = [r["gen_tps"] for r in sel if r["gen"] > 1]
        mtp = [100.0 * r["draft_ok"] / r["draft_all"] for r in sel if r["draft_all"]]
        hits = [r["hit"] for r in sel if "hit" in r]
        pcie = [r["pcie_pct"] for r in sel if "pcie_pct" in r]
        print("%-16s %5d %11.1f %10.1f %9s %9s %8s %8s" % (
            "%d-%s" % (lo, "inf" if hi > 10 ** 8 else hi), len(sel), per_k, rt,
            ("%.1f" % (sum(gt) / len(gt))) if gt else "-",
            ("%.1f" % (sum(mtp) / len(mtp))) if mtp else "-",
            ("%.1f" % (sum(hits) / len(hits))) if hits else "-",
            ("%.2f" % (sum(pcie) / len(pcie))) if pcie else "-",
        ))

    print()
    print("累计计数器（自本次启动）")
    print("  route tail skip (routed-stream 同族机制): %d missed experts / %d entries" % (tail_skip, tail_entries))
    if parks:
        tot_tok = sum(p[0] for p in parks)
        tot_ms = sum(p[1] for p in parks)
        print("  conversation cache park: %d 次 / %d tokens / %.1f ms 合计（每次中位 %.1f ms）" % (
            len(parks), tot_tok, tot_ms, sorted(p[1] for p in parks)[len(parks) // 2]))
    if suffix:
        a = sum(x[0] for x in suffix)
        b = sum(x[1] for x in suffix)
        print("  suffix drafts: %d windows, %d/%d = %.1f%%" % (len(suffix), a, b, 100.0 * a / b if b else 0))

    # 关键结论行
    if reqs:
        big = max(reqs, key=lambda r: r["tok"])
        print()
        print("最长一条: %d tokens, read %d ms (%.1f tok/s), gen %d in %d ms (%.1f tok/s)" % (
            big["tok"], big["read_ms"], big["read_tps"], big["gen"], big["gen_ms"], big["gen_tps"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
