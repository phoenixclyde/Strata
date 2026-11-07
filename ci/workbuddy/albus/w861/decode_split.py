# -*- coding: utf-8 -*-
"""w861_decode_split.py -- 只看 decode 侧：按 prompt 桶算 gen tok/s 与每 token 的 decode 成本。

为什么：w861_time_weight 算出 gen 占总时间 55%，>64K 档占 gen 的 72%。
但"decode 41.6-51.1 tok/s 不随长度变化"是旧结论，必须按桶重算，才知道是
"长上下文掉速"还是"只是生成 token 多"。
"""
from __future__ import annotations

import re
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else "/data/strata-huihui-ud-iq4_xs.log"

RE = re.compile(
    r"strata serve: prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms "
    r"\(([\d.]+) tok/s\), (\d+) generated in (\d+) ms \(([\d.]+) tok/s\), "
    r"drafts accepted (\d+) of (\d+), (\d+) checkpoints")


def main() -> int:
    rows = []
    with open(LOG, "r", encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            m = RE.search(ln)
            if not m:
                continue
            rows.append(dict(tok=int(m.group(1)), reused=int(m.group(2)),
                             rtok=int(m.group(3)), rms=int(m.group(4)),
                             gtok=int(m.group(6)), gms=int(m.group(7)),
                             acc=int(m.group(10)), dr=int(m.group(11))))
    print("n=%d" % len(rows))
    # prompt 桶 × gen 长度桶 的二维：decode ms/token
    PB = [(0, 1024), (1024, 8192), (8192, 16384), (16384, 65536), (65536, 10 ** 9)]
    GB = [(1, 64), (64, 256), (256, 1024), (1024, 10 ** 9)]
    print("\n=== decode ms/token  (行=prompt 桶, 列=gen 桶) ===")
    hdr = "%-16s" % "prompt\\gen"
    for lo, hi in GB:
        hdr += " %14s" % ("%d-%d" % (lo, hi) if hi < 10 ** 9 else "%d+" % lo)
    print(hdr)
    for plo, phi in PB:
        line = "%-16s" % ("%d+" % plo if phi > 10 ** 8 else "%d-%d" % (plo, phi))
        for glo, ghi in GB:
            sel = [r for r in rows if plo <= r["tok"] < phi and glo <= r["gtok"] < ghi]
            if not sel:
                line += " %14s" % "-"
            else:
                ms = sum(r["gms"] for r in sel)
                tk = sum(r["gtok"] for r in sel)
                line += " %14s" % ("%.1fms/%dtok n=%d" % (ms / max(tk, 1), tk, len(sel)))
        print(line)

    print("\n=== 按 prompt 桶：gen 速度与总生成量 ===")
    print("%-14s %6s %10s %10s %10s %8s %8s"
          % ("prompt", "n", "gen_tok", "gen_s", "tok/s", "ms/tok", "acc%"))
    for plo, phi in PB:
        sel = [r for r in rows if plo <= r["tok"] < phi]
        if not sel:
            continue
        tk = sum(r["gtok"] for r in sel)
        ms = sum(r["gms"] for r in sel)
        accn = sum(r["acc"] for r in sel)
        accd = sum(r["dr"] for r in sel)
        print("%-14s %6d %10d %10.1f %10.1f %8.1f %7.1f%%"
              % ("%d+" % plo if phi > 10 ** 8 else "%d-%d" % (plo, phi),
                 len(sel), tk, ms / 1e3, tk / (ms / 1e3) if ms else 0,
                 ms / max(tk, 1), 100.0 * accn / accd if accd else 0))
    # 单条最长生成
    rows.sort(key=lambda r: r["gtok"], reverse=True)
    print("\n=== 生成最长的 8 条 ===")
    for r in rows[:8]:
        print("  prompt=%-7d gen=%-6d gen_ms=%-8d %.1f tok/s  acc=%d/%d"
              % (r["tok"], r["gtok"], r["gms"],
                 r["gtok"] / (r["gms"] / 1e3) if r["gms"] else 0, r["acc"], r["dr"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
