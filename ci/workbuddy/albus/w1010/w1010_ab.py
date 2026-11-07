#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1010 A/B: does the 2K prefill take a different path because of CPU_SHARE_MAX?

Why: `stream_all_min()` falls back to `cpu_share_max()` (prefill.cpp:257-262), and production
sets STRATA_PREFILL_CPU_SHARE_MAX=3072.  So a chunk below 3072 tokens takes the **staged**
walk (routed-only streaming, ring 8) and one at or above it takes **stream-all**.  Our 2K
prompts sit just under that line: `host grouping` is 92 ms at 2083 tokens and 28-50 ms at
4128+, and `wait copy` steps the same way.  P129 pinned 3072 "conservatively" and its own note
says the 1024-3072 interval was never measured on this card.

So: A = 3072 (today), B = 1024 (2K becomes stream-all).  Restart-state is controlled by
measuring A, B, then A again after the restore.

Usage (on 166):  python3 w1010_ab.py [--arm B|A|baseline] [--n 8]
"""
import argparse
import json
import os
import re
import subprocess
import time
import urllib.request

URL = "http://127.0.0.1:8090"
CFG = "/data/strata-huihui-ud-iq4_xs.json"
HOSTCFG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
CONTAINER = "strata166-407"
LOG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log"

VOCAB = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike "
         "november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee "
         "zulu amber basalt cobalt dune ember fjord granite harbor inlet jetty kernel").split()
HEAD = re.compile(r"strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms")
PH = re.compile(r"([A-Za-z][A-Za-z0-9+: /]*?) (\d+) \(\d+\.\d%\)")


def prompt(tokens, salt):
    import random
    rnd = random.Random(tokens * 7919 + salt)
    return " ".join([str(salt)] + [rnd.choice(VOCAB) for _ in range(max(1, int(tokens * 0.78)))])


def ask(p, max_tokens=2, timeout=600):
    body = json.dumps({"model": "probe", "messages": [{"role": "user", "content": p}],
                       "max_tokens": max_tokens, "temperature": 0, "stream": True}).encode()
    req = urllib.request.Request(URL + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            if b"[DONE]" in raw:
                break
    return time.perf_counter() - t0


def measure(tag, lengths, n):
    out = []
    for L in lengths:                      # one throwaway per length: the first is cold (PLE pages)
        ask(prompt(L, 999))
    off = os.path.getsize(LOG)
    for L in lengths:
        for rep in range(n):
            t = ask(prompt(L, rep * 101 + 11))
            out.append((tag, L, t))
    time.sleep(1.5)
    with open(LOG, "rb") as f:
        f.seek(off)
        new = f.read().decode("utf-8", "replace")
    rows = []
    for line in new.splitlines():
        m = HEAD.search(line)
        if not m:
            continue
        d = {k.strip(): int(v) for k, v in PH.findall(line[m.end():])}
        d["_tok"] = int(m.group(1))
        d["_gpu"] = int(m.group(2))
        rows.append(d)
    return out, rows


def summarize(tag, rows):
    if not rows:
        print("%s: no phase lines" % tag)
        return
    def med(k):
        v = [r.get(k, 0) for r in rows]
        v.sort()
        return v[len(v) // 2]
    tok = med("_tok")
    print("%s\tn=%d\ttokens=%d\tgpu=%d\tgu=%d\tdn=%d\tdequant=%d\twaitcopy=%d\thostgrp=%d"
          % (tag, len(rows), tok, med("_gpu"), med("gemm gate/up"), med("gemm down"),
             med("dequant"), med("wait copy"), med("host grouping")))
    cv = lambda v: (100.0 * (sum((x - sum(v) / len(v)) ** 2 for x in v) / len(v)) ** 0.5 / (sum(v) / len(v)))
    print("   CV%% gpu=%.2f gu=%.2f hostgrp=%.1f" %
          (cv([r["_gpu"] for r in rows]), cv([r.get("gemm gate/up", 0) for r in rows]),
           cv([r.get("host grouping", 0) for r in rows])))


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def set_max(val):
    """Targeted text edit of the one value, so the diff is one number (not a reformat)."""
    bak = HOSTCFG + ".bak_w1010"
    if not os.path.exists(bak):
        sh("cp %s %s" % (HOSTCFG, bak))
    s = open(HOSTCFG, encoding="utf-8").read()
    new = re.sub(r'("STRATA_PREFILL_CPU_SHARE_MAX"\s*:\s*)"\d+"', r'\g<1>"%d"' % val, s)
    assert new != s or ('"%d"' % val) in s, "value not found"
    open(HOSTCFG, "w", encoding="utf-8", newline="\n").write(new)
    return val


def restart():
    sh("docker restart %s" % CONTAINER)
    for _ in range(120):
        time.sleep(2)
        r = sh("curl -s -m 3 localhost:8090/health")
        if '"ok"' in r.stdout and "loaded" in r.stdout:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--lengths", default="1735,6915")
    a = ap.parse_args()
    lengths = [int(x) for x in a.lengths.split(",")]

    tag = time.strftime("%H%M")
    print("# baseline (current process, CPU_SHARE_MAX as configured)", flush=True)
    _, rows = measure("A-before-" + tag, lengths, a.n)
    summarize("A-before", rows)

    print("# arm B: CPU_SHARE_MAX=1024 (2K becomes stream-all), restart", flush=True)
    print("   wrote STRATA_PREFILL_CPU_SHARE_MAX=%s" % set_max(1024), flush=True)
    print("   health:", restart(), flush=True)
    time.sleep(3)
    _, rows = measure("B-" + tag, lengths, a.n)
    summarize("B(1024)", rows)

    print("# restore the original value, restart", flush=True)
    print("   wrote STRATA_PREFILL_CPU_SHARE_MAX=%s" % set_max(3072), flush=True)
    print("   health:", restart(), flush=True)
    time.sleep(3)
    _, rows = measure("A-after-" + tag, lengths, a.n)
    summarize("A-after", rows)
    print("# md5 of the config now:", sh("md5sum %s" % HOSTCFG).stdout.strip(), flush=True)


if __name__ == "__main__":
    main()
