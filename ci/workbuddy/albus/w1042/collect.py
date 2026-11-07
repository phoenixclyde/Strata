#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1042: pull the window artefacts back to the Windows workspace and rebuild the
broken P2 timing statistics from the raw harness lines (no new downtime needed).

The harness ab_w1042.py crashed in decode_summary (DEC=0 -> statistics.mean([])),
so t_T1.json / t_T2.json were never written.  Every prefill line was already
printed to window.log, so the samples are recoverable byte-for-byte.
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

W = r"D:/workbuddy_space/strata_ws/albus/w1042"
R = "/home/albus/strata166/tmp/w1042"
os.makedirs(W, exist_ok=True)

PULL = ["window.log", "build.log", "port_attn.sh", "window_w1042.sh",
        "needle1042.py", "ab_w1042.py", "cfgP_kvg.json", "cfgP_attn.json",
        "needle.prompts.json"]


def main():
    for name in PULL:
        rc, out, err = _sshutil.run_remote("cat %s/%s 2>/dev/null" % (R, name), timeout=120)
        if rc == 0 and out:
            io.open(os.path.join(W, name), "w", encoding="utf-8", newline="\n").write(out)
            print("pulled %-24s %6d B" % (name, len(out)))
        else:
            print("skip   %-24s (%s)" % (name, err[-60:] if err else "empty"))

    # index.json of the four numeric arms
    for arm in "ABC":
        rc, out, err = _sshutil.run_remote("cat %s/n_%s/index.json" % (R, arm), timeout=60)
        if rc == 0 and out:
            io.open(os.path.join(W, "n_%s_index.json" % arm), "w", encoding="utf-8",
                    newline="\n").write(out)

    rc, out, err = _sshutil.run_remote("cat %s/window.log" % R, timeout=120)
    log = out
    io.open(os.path.join(W, "window.log"), "w", encoding="utf-8", newline="\n").write(log)

    # ---- parse P2 ----
    # the log is sequential: "=== P2 timing: off ===" ... "=== P2 timing: DP4A on ===" ...
    arms = {}
    cur = None
    for line in log.splitlines():
        m = re.match(r"\d\d:\d\d:\d\d === P2 timing: (.+) ===$", line)
        if m:
            cur = "off" if "off" in m.group(1) else "on"
            arms[cur] = []
            continue
        if line.startswith("=== P3"):
            cur = None
        if cur:
            # the harness prints two spaces before attn=; do not hard-code single spaces
            m = re.match(r"prefill\s+(\d+) -> tokens=(\d+) gpu=(\d+) wall=(\d+)\s+"
                         r"attn=(\d+)\s+gu=(\d+)\s+down=(\d+)\s+deq=(\d+)", line)
            if m:
                arms[cur].append({k: int(v) for k, v in zip(
                    ("shape", "tokens", "gpu", "wall", "attn", "gu", "down", "deq"), m.groups())})
    out_obj = {"source": R + "/window.log", "arms": arms}
    io.open(os.path.join(W, "p2_raw.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(out_obj, ensure_ascii=False, indent=1))

    # paired per-shape statistics + 2xCV band
    import statistics as st
    res = {}
    for shape in (2500, 8000, 16000):
        a = [r for r in arms.get("off", []) if r["shape"] == shape]
        b = [r for r in arms.get("on", []) if r["shape"] == shape]
        if not a or not b:
            continue
        row = {"n_off": len(a), "n_on": len(b)}
        for key in ("gpu", "wall", "attn"):
            va, vb = [r[key] for r in a], [r[key] for r in b]
            ma, mb = st.mean(va), st.mean(vb)
            cva = 100.0 * st.pstdev(va) / ma if len(va) > 1 else 0.0
            cvb = 100.0 * st.pstdev(vb) / mb if len(vb) > 1 else 0.0
            band = 2 * max(cva, cvb)
            delta = 100.0 * (mb / ma - 1)
            row[key] = {"mean_off": round(ma, 1), "mean_on": round(mb, 1),
                        "delta_pct": round(delta, 2), "cv_off": round(cva, 2),
                        "cv_on": round(cvb, 2), "band_2cv": round(band, 2),
                        "verdict": "REAL" if abs(delta) >= band else "within noise"}
        res["shape_%d" % shape] = row
    io.open(os.path.join(W, "p2_stats.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(res, ensure_ascii=False, indent=1))
    print("\n=== P2 paired statistics ===")
    for k, v in res.items():
        print(k, {f: (v[f]["delta_pct"], v[f]["band_2cv"], v[f]["verdict"])
                  for f in ("gpu", "wall", "attn")})

    # ---- parse P3 needle ----
    needles = {}
    for line in log.splitlines():
        m = re.match(r"S([12]) (16K|28K)\s+hit=(\w+) prompt=(\d+) cached=(\d+) ([\d.]+)s", line)
        if m:
            tag = "off" if m.group(1) == "1" else "on"
            needles.setdefault(tag, {})[m.group(2)] = {
                "hit": m.group(3) == "True", "prompt_tokens": int(m.group(4)),
                "cached": int(m.group(5)), "secs": float(m.group(6))}
    io.open(os.path.join(W, "p3_needle.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(needles, ensure_ascii=False, indent=1))
    print("\n=== P3 needle ===", json.dumps(needles))


if __name__ == "__main__":
    main()
