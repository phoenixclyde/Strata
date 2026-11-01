#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prefill_probe -- TTFT and prefix reuse, measured without touching the service.

Why: every measurement so far has been decode (tok/s). But a single-stream user feels
prefill first -- the wait before the first token -- and that wait is what `--prompt-cache-every`
and `--conversation-cache-mib` are supposed to cut on the second turn of a conversation.

Two questions, both answerable with plain HTTP against the live service:

  Q1  How does TTFT scale with prompt length? (prefill throughput in prompt tokens/s)
  Q2  Does repeating the same prefix make the second call faster? (is caching actually working)

Method notes:
  * TTFT needs a STREAMING request: the first SSE chunk is the first generated token, so the
    time to it is prefill + one decode step. Non-streaming would measure the whole generation.
  * max_tokens is kept small (8) so each call frees the GPU quickly.
  * the first call of each cell is discarded as warm-up (that mistake once moved a bench's CV
    from 1.06% to 18.36%).
  * actual prompt_tokens come back in `usage`, so the length axis is the machine's count, not
    my estimate from characters.

Usage:
  prefill_probe.py                 # length sweep + repeat test
  prefill_probe.py --quick         # smaller n
"""
import argparse
import json
import random
import statistics
import time
import urllib.request

URL = "http://127.0.0.1:8090"
FILLER = "The quick brown fox jumps over the lazy dog. "


def make_prompt(approx_tokens, salt=""):
    """Approximate a prompt of the requested size; the real count is read from usage."""
    n = max(1, int(approx_tokens / 11))          # ~11 tokens per sentence at ~4.2 chars/token
    return (salt + FILLER * n).strip()


def make_unique_prompt(approx_tokens):
    """A prompt that cannot share a prefix with anything, for measuring COLD prefill.

    Repeating one filler made every shorter prompt a prefix of every longer one, so the whole
    length sweep came back flat at ~250 ms (28k tok/s, i.e. a cache hit every time). Random
    words make reuse impossible, which is the only way to see what prefill actually costs.
    """
    rnd = random.Random(approx_tokens * 7919)
    vocab = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike "
             "november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee "
             "zulu amber basalt cobalt dune ember fjord granite harbor inlet jetty kernel").split()
    words = [rnd.choice(vocab) for _ in range(max(1, int(approx_tokens * 0.78)))]
    return " ".join(words)


def ask_ttft(prompt, max_tokens=8, timeout=300):
    """One streaming request. Returns (ttft_s, total_s, prompt_tokens, completion_tokens)."""
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
    ptok = ctok = 0
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
            # The first frame carries only the role delta, so timing it would report the
            # round trip instead of prefill (measured: 2.4 ms "TTFT" for 1912 tokens).
            # TTFT is the first chunk that actually carries a token.
            ch = (d.get("choices") or [{}])[0]
            piece = (ch.get("delta") or {}).get("content")
            if ttft is None and piece:
                ttft = time.perf_counter() - t0
            u = d.get("usage") or {}
            if u:
                ptok = u.get("prompt_tokens", ptok)
                ctok = u.get("completion_tokens", ctok)
    total = time.perf_counter() - t0
    return (ttft if ttft is not None else total), total, ptok, ctok


def med(xs):
    return statistics.median(xs) if xs else float("nan")


def cv(xs):
    if len(xs) < 2:
        return 0.0
    m = statistics.fmean(xs)
    return 100.0 * statistics.pstdev(xs) / m if m else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--warmup", type=int, default=1)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    n = 2 if a.quick else a.n

    # ---- Q1: TTFT vs prompt length -------------------------------------------------
    print("Q1  COLD TTFT vs prompt length (random content, no prefix reuse possible)")
    print("%-10s %-10s %10s %10s %8s %12s" %
          ("approx", "real tok", "TTFT ms", "CV", "n", "prefill tok/s"))
    print("-" * 70)
    rows = []
    for approx in (256, 512, 1024, 2048, 4096, 8192):
        # Random content: no prefix can be reused, so this is cold prefill every time.
        # No warm-up either -- "warm" for a cold measurement is just a second cold call.
        tts, ptok, tots = [], 0, []
        for _ in range(n):
            ttft, tot, pt, _ct = ask_ttft(make_unique_prompt(approx))
            tts.append(ttft * 1000.0)
            tots.append(tot * 1000.0)
            ptok = pt or ptok
        thr = (ptok / (med(tts) / 1000.0)) if med(tts) > 0 else 0.0
        rows.append((approx, ptok, med(tts), cv(tts), n, thr))
        print("%-10d %-10d %10.1f %9.1f%% %8d %12.0f" %
              (approx, ptok, med(tts), cv(tts), n, thr))

    # ---- Q2: does repeating the same prefix help? ----------------------------------
    print()
    print("Q2  same prompt repeated (does --prompt-cache-every actually reuse the prefix?)")
    print("%-8s %10s %10s %8s %s" % ("call", "TTFT ms", "vs 1st", "tok", "note"))
    print("-" * 62)
    base = make_prompt(2048, salt="Reuse cell. ")
    first = None
    for i in range(5):
        ttft, _tot, pt, _ct = ask_ttft(base)
        ms = ttft * 1000.0
        if first is None:
            first = ms
            note = "cold"
        else:
            note = "cached" if ms < first * 0.5 else "no reuse"
        print("%-8d %10.1f %9.0f%% %8d %s" %
              (i + 1, ms, 100.0 * ms / first if first else 0, pt, note))

    # ---- Q3: different content, same length (control for Q2) -----------------------
    print()
    print("Q3  control: different content, same length (a cache must NOT help here)")
    for i in range(3):
        ttft, _tot, pt, _ct = ask_ttft(make_prompt(2048, salt="Control %d. " % i))
        print("   call %d  TTFT %7.1f ms  tok %d" % (i + 1, ttft * 1000.0, pt))

    # ---- Q4: incremental reuse, i.e. what a multi-turn conversation actually pays --------
    print()
    print("Q4  incremental prefix (turn 2 = turn 1 + 400 new tokens; this is the real chat shape)")
    p1 = make_unique_prompt(2000)
    p2 = p1 + " " + make_unique_prompt(400)
    t1, _x, pt1, _c = ask_ttft(p1)
    t2, _x, pt2, _c = ask_ttft(p2)
    fresh = make_unique_prompt(2400)
    t3, _x, pt3, _c = ask_ttft(fresh)
    print("   turn 1  P1  %5d tok  TTFT %8.1f ms   (cold)" % (pt1, t1 * 1000))
    print("   turn 2  P2  %5d tok  TTFT %8.1f ms   (P1 + 400 new)" % (pt2, t2 * 1000))
    print("   control P3  %5d tok  TTFT %8.1f ms   (same size, nothing shared)" % (pt3, t3 * 1000))
    print("   => incremental pays %.0f%% of the fresh cost (100%% = no reuse at all)"
          % (100.0 * t2 / t3 if t3 else 0))

    print()
    print("Reading: Q2 faster than Q3 means the prefix cache is doing its job; Q2 ~= Q3 means")
    print("it is not, and every turn of a conversation pays full prefill again.")


if __name__ == "__main__":
    main()
