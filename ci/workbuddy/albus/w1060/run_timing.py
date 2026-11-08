#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1060 timing runner: fresh prompts of N tokens (synthesized text), max_tokens=1,
# ground truth = engine log "prefill timing" lines. Warm >=2 per container (W825 lesson).
# usage: run_timing.py <port> <tag> <sizes,comma> <reps> <out.json>
import json
import sys
import time
import urllib.request

PORT, TAG, SIZES, REPS, OUT = int(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]

BASE = ("The quick brown fox jumps over the lazy dog while engineers tune gfx906 kernels. "
        "Paragraph marker %d keeps each segment unique so no conversation cache can hit. "
        "Prefill throughput depends on chunking, expert routing, and memory residency. ")


def synth(ntok):
    # ~4 chars/token heuristic; numbered paragraphs stay unique
    parts = []
    i = 0
    total = 0
    while total < ntok:
        p = BASE % i
        parts.append(p)
        total += len(p.split())
        i += 1
    return " ".join(parts)


def post(txt):
    body = {"model": "default-big", "messages": [{"role": "user", "content": txt}],
            "max_tokens": 1, "temperature": 0.0}
    req = urllib.request.Request("http://127.0.0.1:%d/v1/chat/completions" % PORT,
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=3600) as r:
        j = json.loads(r.read())
    u = j.get("usage", {}) or {}
    return {"wall_s": round(time.time() - t0, 2), "prompt_tokens": u.get("prompt_tokens")}


out = {"tag": TAG, "runs": []}
# warm
for w in range(2):
    post(synth(512))
    print("warm %d done" % w, flush=True)
for size in [int(x) for x in SIZES.split(",")]:
    for rep in range(REPS):
        rec = post(synth(size))
        rec.update({"size": size, "rep": rep})
        out["runs"].append(rec)
        print("size %d rep %d wall %.2fs ptok %s" % (size, rep, rec["wall_s"], rec["prompt_tokens"]), flush=True)
json.dump(out, open(OUT, "w"), indent=1)
print("WROTE", OUT)
