#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mechanical G1..G5 verdict for the R103 install window (W1043, NOT EXECUTED).

Criteria are pre-registered in albus/w1043/LONGCTX_GATE.md §4 and MUST NOT be
edited after the window runs.  Pure local JSON in / JSON out -- no GPU.

    python3 judge.py --grid-off grid_off.json --grid-on grid_on.json \
                     --kl kl.json --timing timing.json --floor-ok 1 \
                     --out verdict.json
    python3 judge.py --self-test
"""
import argparse
import io
import json
import os
import sys


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


def judge(grid_off, grid_on, kl, timing, floor_ok):
    reasons = {}
    v = {}

    # G1 combo build floor (both arms carry --kv-grow, P510)
    v["G1"] = bool(floor_ok)
    reasons["G1"] = "A/B byte-identical at every point" if v["G1"] else "build floor differs"

    # G2 candidate cost <= the KV-precision budget we already accepted, at EVERY length
    bad = [k for k, x in kl.items()
           if not (isinstance(x.get("kl_cand"), (int, float))
                   and isinstance(x.get("kl_anchor"), (int, float))
                   and x["kl_cand"] <= x["kl_anchor"])]
    v["G2"] = len(kl) >= 4 and not bad
    reasons["G2"] = "%d lengths, violations=%s" % (len(kl), bad or "none")

    # G3 no long-context cliff: KL(C)/KL(D) at 32K must not be more than 2x
    # worse than at 20K. The 2x is a project convention, not a community standard.
    def ratio(key):
        x = kl.get(key)
        if not x or not x.get("kl_anchor"):
            return None
        return x["kl_cand"] / x["kl_anchor"]

    r20, rlong = ratio("20K"), ratio("32K")
    v["G3"] = r20 is not None and rlong is not None and rlong <= 2.0 * r20
    reasons["G3"] = "ratio@20K=%s ratio@32K=%s limit=%s" % (
        round(r20, 3) if r20 is not None else None,
        round(rlong, 3) if rlong is not None else None,
        round(2.0 * r20, 3) if r20 is not None else None)

    # G4 task grid: candidate hit count >= baseline, no cached points, same keys
    off, on = grid_off.get("grid", {}), grid_on.get("grid", {})
    invalid = grid_off.get("invalid", []) + grid_on.get("invalid", [])
    same = set(off) == set(on) and bool(off)
    nh_off = sum(1 for x in off.values() if x.get("hit"))
    nh_on = sum(1 for x in on.values() if x.get("hit"))
    v["G4"] = same and not invalid and nh_on >= nh_off
    reasons["G4"] = "keys_equal=%s hits off=%d on=%d invalid=%d" % (same, nh_off, nh_on, len(invalid))

    # G5 wall clock: candidate may not be slower than baseline by more than that run's 2xCV
    badt = []
    for k, x in timing.items():
        d, band = x.get("delta_pct"), x.get("band_2cv")
        if not isinstance(d, (int, float)) or not isinstance(band, (int, float)) or d > band:
            badt.append(k)
    v["G5"] = bool(timing) and not badt
    reasons["G5"] = "%d shapes, violations=%s" % (len(timing), badt or "none")

    return {"G1": v["G1"], "G2": v["G2"], "G3": v["G3"], "G4": v["G4"], "G5": v["G5"],
            "go": all(v.values()), "reasons": reasons}


def self_test():
    def grid(hits):
        return {"grid": {"%d@%d%%" % (n, d): {"hit": h, "cached": 0}
                         for n in (16000, 32000, 64000) for d in (0, 50, 100)
                         for h in [hits]}, "invalid": []}
    kl = {"1K": {"kl_cand": .00037, "kl_anchor": .00155},
          "8K": {"kl_cand": .00345, "kl_anchor": .01113},
          "16K": {"kl_cand": .01429, "kl_anchor": .01699},
          "20K": {"kl_cand": .18750, "kl_anchor": .38387},
          "32K": {"kl_cand": .25, "kl_anchor": .50}}
    timing = {"8000": {"delta_pct": -2.72, "band_2cv": 1.34},
              "16000": {"delta_pct": -1.72, "band_2cv": 0.36}}
    cases = [("全过", grid(True), grid(True), kl, timing, 1, True),
             ("G1 floor 破", grid(True), grid(True), kl, timing, 0, False),
             ("G2 32K 反超锚", grid(True), grid(True),
              dict(kl, **{"32K": {"kl_cand": .9, "kl_anchor": .5}}), timing, 1, False),
             ("G3 长度悬崖", grid(True), grid(True),
              dict(kl, **{"32K": {"kl_cand": .49, "kl_anchor": .50}}), timing, 1, False),
             ("G4 掉命中", grid(True), grid(False), kl, timing, 1, False),
             ("G4 有缓存点", {"grid": grid(True)["grid"], "invalid": ["16K@0% cached_tokens=999"]},
              grid(True), kl, timing, 1, False),
             ("G5 变慢超带宽", grid(True), grid(True), kl,
              dict(timing, **{"8000": {"delta_pct": +3.0, "band_2cv": 1.34}}), 1, False)]
    bad = 0
    for name, goff, gon, k, t, floor, want in cases:
        v = judge(goff, gon, k, t, floor)
        ok = v["go"] == want
        bad += 0 if ok else 1
        print("  %-20s %-4s (go=%s failed=%s)" %
              (name, "PASS" if ok else "FAIL", v["go"],
               [x for x in "G1 G2 G3 G4 G5".split() if not v[x]]))
    print("JUDGE_SELF_TEST: %d/%d" % (len(cases) - bad, len(cases)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid-off")
    ap.add_argument("--grid-on")
    ap.add_argument("--kl")
    ap.add_argument("--timing")
    ap.add_argument("--floor-ok", type=int, default=0)
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    for p in (a.grid_off, a.grid_on, a.kl, a.timing):
        if not p or not os.path.isfile(p):
            print("missing input: %s" % p)
            return 1
    v = judge(load(a.grid_off), load(a.grid_on), load(a.kl), load(a.timing), a.floor_ok)
    print(json.dumps(v, ensure_ascii=False, indent=1))
    if a.out:
        io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(v, ensure_ascii=False, indent=1))
    return 0 if v["go"] else 1


if __name__ == "__main__":
    sys.exit(main())
