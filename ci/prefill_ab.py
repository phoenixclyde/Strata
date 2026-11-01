#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prefill_ab -- does an incremental prompt reuse the prefix? measured with repeats.

R40's verdict needs one number: TTFT(turn 2 = turn 1 + 400 new tokens) divided by
TTFT(an equally long prompt that shares nothing). 100% means no reuse at all.

Why this is a separate script: prefill's noise is an order of magnitude worse than decode's
(measured CV 71-96% on cold TTFT), so a single pair proves nothing. Each sample is a fresh
conversation, and the reported figure is the median of n samples plus its CV.

The control has to be built the same way as the incremental prompt (random words, unique
content): an earlier attempt used one repeated filler for everything, which made the short
prompts prefixes of the long ones and reported 28k tok/s -- a cache hit, not a measurement.

Usage:  prefill_ab.py [--n 3]
Exit 0 always; the verdict line is what to read.
"""
import argparse
import json
import random
import statistics
import time
import urllib.request

URL = "http://127.0.0.1:8090"
VOCAB = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike "
         "november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee "
         "zulu amber basalt cobalt dune ember fjord granite harbor inlet jetty kernel "
         "lantern meadow nectar onyx prairie quartz ripple summit tundra umber vertex willow").split()


def words(n, seed):
    rnd = random.Random(seed)
    return " ".join(rnd.choice(VOCAB) for _ in range(n))


def ask_ttft(prompt, max_tokens=4, timeout=300):
    """Streaming request; TTFT = first chunk that carries a token (not the role delta)."""
    body = json.dumps({
        "model": "probe",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": True,
    }).encode()
    req = urllib.request.Request(URL + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    ttft = None
    ptok = 0
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                d = json.loads(payload)
            except Exception:                     # noqa: BLE001
                continue
            piece = ((d.get("choices") or [{}])[0].get("delta") or {}).get("content")
            if ttft is None and piece:
                ttft = time.perf_counter() - t0
            u = d.get("usage") or {}
            if u:
                ptok = u.get("prompt_tokens", ptok)
    return (ttft if ttft is not None else time.perf_counter() - t0), ptok


def cv(xs):
    if len(xs) < 2:
        return 0.0
    m = statistics.fmean(xs)
    return 100.0 * statistics.pstdev(xs) / m if m else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--base", type=int, default=2000, help="turn-1 prompt size (words)")
    ap.add_argument("--extra", type=int, default=400, help="tokens added on turn 2 (words)")
    a = ap.parse_args()

    print("incremental-reuse A/B   n=%d   turn1=%dw  turn2=+%dw" % (a.n, a.base, a.extra))
    print("%-5s %10s %10s %10s %8s" % ("#", "turn1 ms", "turn2 ms", "fresh ms", "ratio"))
    print("-" * 52)
    ratios, absolutes = [], []
    for i in range(a.n):
        p1 = words(a.base, seed=1000 + i * 17)
        p2 = p1 + " " + words(a.extra, seed=5000 + i * 17)
        fresh = words(a.base + a.extra, seed=9000 + i * 17)
        t1, n1 = ask_ttft(p1)
        t2, n2 = ask_ttft(p2)
        t3, n3 = ask_ttft(fresh)
        r = 100.0 * t2 / t3 if t3 else 0.0
        ratios.append(r)
        absolutes.append(t2 * 1000.0)
        print("%-5d %10.1f %10.1f %10.1f %7.0f%%" %
              (i + 1, t1 * 1000, t2 * 1000, t3 * 1000, r))

    med = statistics.median(ratios)
    print()
    print("median turn2/fresh = %.0f%%  (CV %.0f%%)   turn2 absolute median %.0f ms"
          % (med, cv(ratios), statistics.median(absolutes)))
    print("verdict: %s" % ("REUSE WORKING" if med < 40 else
                           ("PARTIAL" if med < 75 else "NO REUSE (100% = every turn full prefill)")))
    print("threshold from the plan: <40% (i.e. >=60% of the prompt is served from cache)")


if __name__ == "__main__":
    main()
