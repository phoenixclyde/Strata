#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prefill_multiturn -- the real chat shape, which the previous probe got wrong.

WHAT WAS WRONG
--------------
prefill_ab built turn 2 as `P1 + new words`, i.e. it skipped the model's own reply. A real
conversation sends turn 2 as

    [user: P1] [assistant: reply1] [user: P2]

so the prompt of turn 2 is *turn 1's prompt plus turn 1's reply plus the new question*. Against
that shape the engine's prefix test (`conversation_prefix`: `std::equal(c.ids, prompt.begin())`)
matches the whole of turn 1 including the reply, which is exactly what a parked conversation holds.

With the reply omitted, turn 2 diverges from the parked state at the first new token, so 0 reuse
was the correct answer to the wrong question.

This probe therefore drives a real multi-turn conversation through /v1/chat/completions and
compares turn 2 against a single-turn prompt of the same total length.

Usage: prefill_multiturn.py [--n 3] [--turn1 1200] [--turn2 300]
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


def ask(messages, max_tokens=24, timeout=400):
    """Streaming; returns (ttft_s, total_s, prompt_tokens, completion_tokens, text)."""
    body = json.dumps({
        "model": "probe", "messages": messages, "max_tokens": max_tokens,
        "temperature": 0, "stream": True,
    }).encode()
    req = urllib.request.Request(URL + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    ttft = None
    out, ptok, ctok = [], 0, 0
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
            ch = (d.get("choices") or [{}])[0]
            piece = (ch.get("delta") or {}).get("content")
            if ttft is None and piece:
                ttft = time.perf_counter() - t0
            if piece:
                out.append(piece)
            u = d.get("usage") or {}
            if u:
                ptok = u.get("prompt_tokens", ptok)
                ctok = u.get("completion_tokens", ctok)
    total = time.perf_counter() - t0
    return (ttft if ttft is not None else total), total, ptok, ctok, "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--turn1", type=int, default=1200, help="words in the first user message")
    ap.add_argument("--turn2", type=int, default=300, help="words in the follow-up question")
    a = ap.parse_args()

    print("real multi-turn: turn2 = [user P1][assistant reply1][user P2]")
    print("%-4s %9s %9s %9s %9s %8s" % ("#", "turn1", "turn2", "single", "reply tok", "ratio"))
    print("-" * 62)
    ratios, t2s = [], []
    for i in range(a.n):
        p1 = words(a.turn1, seed=3100 + i * 13)
        p2 = words(a.turn2, seed=7100 + i * 13)

        m1 = [{"role": "user", "content": p1}]
        t1, _x, n1, c1, reply = ask(m1)

        # a real second turn carries the model's own answer
        m2 = [{"role": "user", "content": p1},
              {"role": "assistant", "content": reply},
              {"role": "user", "content": p2}]
        t2, _x, n2, c2, _r2 = ask(m2)

        # control: one turn with the same total length, sharing nothing
        single = p1 + " " + reply + " " + p2
        t3, _x, n3, c3, _r3 = ask([{"role": "user", "content": single}])

        r = 100.0 * t2 / t3 if t3 else 0.0
        ratios.append(r); t2s.append(t2 * 1000)
        print("%-4d %8.0f %8.0f %8.0f %9d %7.0f%%" %
              (i + 1, t1 * 1000, t2 * 1000, t3 * 1000, c1, r))
        print("       prompt tokens: turn1 %d -> turn2 %d ; single %d" % (n1, n2, n3))

    print()
    med = statistics.median(ratios)
    print("median turn2/single = %.0f%%   turn2 median %.0f ms" % (med, statistics.median(t2s)))
    print("verdict: %s" % ("REUSE WORKING" if med < 40 else
                           ("PARTIAL" if med < 75 else "NO REUSE")))
    print("If REUSE WORKING: the engine already reuses across real turns, and the earlier")
    print("'100% no reuse' result only described a prompt that skips the assistant reply.")


if __name__ == "__main__":
    main()
