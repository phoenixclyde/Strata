#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bench_pair -- one process, two metrics: fresh-prompt prefill (TTFT) and steady decode.

Why: bench.py only measures decode; prefill needs a *unique* prompt per rep or the
conversation/prompt cache answers it from cache and TTFT collapses.

  prefill arm : unique random text each rep (~--prefill-tokens), max_tokens=1 -> TTFT
  decode arm  : one fixed short prompt, max_tokens=--decode-tokens -> (t_last - t_first)

Prints per-rep values, median and CV for both.  Exit 0.
"""
import argparse
import json
import random
import statistics
import time
import urllib.request

VOCAB = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike "
         "november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee "
         "zulu amber basalt cobalt dune ember fjord granite harbor inlet jetty kernel "
         "lantern meadow nectar onyx prairie quartz ripple summit tundra umber vertex willow").split()


def text_of(words, seed):
    rnd = random.Random(seed)
    return " ".join(rnd.choice(VOCAB) for _ in range(words))


def stream(url, prompt, mx):
    body = json.dumps({"model": "probe", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": mx, "temperature": 0, "stream": True}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    t_first = None
    usage = {}
    with urllib.request.urlopen(req, timeout=1800) as r:
        for line in r:
            s = line.decode().strip()
            if not s.startswith("data:"):
                continue
            p = s[5:].strip()
            if p == "[DONE]":
                break
            try:
                ev = json.loads(p)
            except json.JSONDecodeError:
                continue
            if ev.get("usage"):
                usage = ev["usage"]
            ch = (ev.get("choices") or [{}])[0]
            delta = ch.get("delta") or {}
            if t_first is None and (delta.get("content") or delta.get("reasoning_content")):
                t_first = time.time()
    return t0, t_first, time.time(), usage


def stats(v):
    med = statistics.median(v)
    cv = (statistics.pstdev(v) / med * 100.0) if len(v) > 1 and med else 0.0
    return med, cv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8090/v1/chat/completions")
    ap.add_argument("--prefill-words", type=int, default=4200, help="~1.56 tok/word on this vocab")
    ap.add_argument("--decode-tokens", type=int, default=256)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()

    pf, dc, pf_tok = [], [], []
    for i in range(a.n):
        t0, t1, t2, u = stream(a.url, text_of(a.prefill_words, a.seed + i), 1)
        if t1 is None:
            t1 = t2
        pf.append(t1 - t0)
        pf_tok.append(int(u.get("prompt_tokens") or 0))
        print("prefill rep%d  ttft %.3f s  prompt_tokens %s" % (i + 1, pf[-1], pf_tok[-1]))

    fixed = "Count from 1 to 40, one number per line."
    for i in range(a.n):
        t0, t1, t2, u = stream(a.url, fixed, a.decode_tokens)
        if t1 is None:
            print("decode rep%d  NO TOKEN" % (i + 1))
            continue
        ntok = int(u.get("completion_tokens") or 0)
        rate = (ntok - 1) / max(t2 - t1, 1e-9)
        dc.append(rate)
        print("decode rep%d  %.2f tok/s  (%.2f s, %d tokens)" % (i + 1, rate, t2 - t1, ntok))

    if pf:
        m, c = stats(pf)
        tokm = statistics.median(pf_tok) if pf_tok else 0
        print("PREFILL ttft median %.3f s  CV %.1f%%  (~%.0f tok/s at %s prompt tokens)"
              % (m, c, (tokm / m if m else 0), tokm))
    if dc:
        m, c = stats(dc)
        print("DECODE  median %.2f tok/s  CV %.1f%%" % (m, c))


if __name__ == "__main__":
    main()
