#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1005 probe: prefill phase table at three lengths, current production config, cold prompts.

Why this exists: R95 has been quoted for five rounds as "dequant 3.9x, wait copy 14x", but those
are *excesses* against a 16K-normalised rate reconstructed from a log that spans many engine
versions.  Mixing versions is how a phase table turns into folklore: the 506-line log has 83
length clusters from at least a dozen builds (some show `gdn 54 ms` at 69 tokens, some have no
`hc read` at all).  So: same binary, same config, unique prompts, n reps per length, and only
the lines this run appends are read.

Usage (on 166):  python3 w1005_probe.py [--reps 3]
Outputs a TSV: tokens, rep, wall, gpu, and every phase in ms.
"""
import argparse
import json
import os
import random
import re
import sys
import time
import urllib.request

URL = "http://127.0.0.1:8090"
LOG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log"
LENGTHS = [2048, 8192, 16384]

HEAD = re.compile(r"strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms, wall (\d+) ms, host staging (\d+) ms:")
PH = re.compile(r"([a-z][a-z0-9+: /]*?) (\d+) \((\d+\.\d)%\)")

VOCAB = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike "
         "november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee "
         "zulu amber basalt cobalt dune ember fjord granite harbor inlet jetty kernel").split()


def prompt(approx_tokens, salt):
    rnd = random.Random(approx_tokens * 7919 + salt)
    n = max(1, int(approx_tokens * 0.78))
    return " ".join([str(salt)] + [rnd.choice(VOCAB) for _ in range(n)])


def ask(p, max_tokens=2, timeout=600):
    body = json.dumps({"model": "probe",
                       "messages": [{"role": "user", "content": p}],
                       "max_tokens": max_tokens, "temperature": 0, "stream": True}).encode()
    req = urllib.request.Request(URL + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
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
            except Exception:
                continue
            u = d.get("usage") or {}
            if u:
                ptok = u.get("prompt_tokens", ptok)
    return time.perf_counter() - t0, ptok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--lengths", default="2048,8192,16384")
    a = ap.parse_args()
    lengths = [int(x) for x in a.lengths.split(",")]

    off = os.path.getsize(LOG)
    print("# log offset %d" % off, flush=True)

    for L in lengths:
        for rep in range(a.reps):
            t, n = ask(prompt(L, rep * 101 + 7))
            print("# asked %d -> %d tokens, %.1f s" % (L, n, t), flush=True)
            time.sleep(0.5)

    time.sleep(2.0)
    with open(LOG, "rb") as f:
        f.seek(off)
        new = f.read().decode("utf-8", "replace")
    lines = [l for l in new.splitlines() if HEAD.search(l)]
    print("tokens\thost\twall\tgpu\t" + "\t".join(
        ["embed+steps", "hc read", "gdn", "qsa proj", "qsa indexer", "qsa select", "qsa attn",
         "router+shared", "host grouping", "gather", "wait copy", "dequant", "gemm gate/up",
         "gemm down", "combine", "ple", "kv stage", "gdn conv+gates", "gdn recurrence",
         "gdn out proj", "hc write"]))
    for l in lines:
        m = HEAD.search(l)
        tok, gpu, wall, host = m.groups()
        d = {k.strip(): v for k, v, _ in PH.findall(l[m.end():])}
        cells = [d.get(k, "") for k in ["embed+steps", "hc read", "gdn", "qsa proj", "qsa indexer",
                                        "qsa select", "qsa attn", "router+shared", "host grouping",
                                        "gather", "wait copy", "dequant", "gemm gate/up",
                                        "gemm down", "combine", "ple", "kv stage", "gdn conv+gates",
                                        "gdn recurrence", "gdn out proj", "hc write"]]
        print("\t".join([tok, host, wall, gpu] + cells))
    print("# %d phase lines captured" % len(lines))


if __name__ == "__main__":
    main()
