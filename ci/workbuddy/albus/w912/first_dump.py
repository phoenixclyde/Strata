#!/usr/bin/env python3
"""W912/R59 exact instrument: full-vocabulary logits of the FIRST window, via STRATA_DUMP_FIRST_LOGITS.

Why this instead of top-20 logprobs: as soon as two runs emit different tokens their contexts diverge and a
position-wise KL compares two different sentences.  The first window has no such problem - it is one
distribution per prompt, conditioned on a prompt both arms see identically - and it is the full vocab, so
the KL is exact rather than truncated at the 20 most likely tokens.

Usage (inside the container, engine started with STRATA_DUMP_FIRST_LOGITS=/data/w912/first.bin):
  python3 first_dump.py collect <arm> [reps]      # writes /data/w912/<arm>_<pid>_<rep>.bin
  python3 first_dump.py compare <a_glob> <b_glob>
"""
import glob
import json
import os
import struct
import sys
import time
import urllib.request

URL = "http://127.0.0.1:8090/v1/chat/completions"
DUMP = "/data/w912/first.bin"
OUTDIR = "/data/w912"

PROMPTS = [
    ("q01", "Name the capital of France in one word."),
    ("q02", "What is 17 * 23? Answer with the number only."),
    ("q03", "Translate 'the quick brown fox' into German."),
    ("q04", "List three prime numbers greater than 20."),
    ("q05", "Explain in one sentence why the sky is blue."),
    ("q06", "Write a Python one-liner that reverses a string."),
    ("q07", "What does the acronym HIP stand for in AMD's stack?"),
    ("q08", "Give one reason a matrix-vector product is bandwidth bound."),
    ("q09", "Complete the sequence: 2, 4, 8, 16,"),
    ("q10", "Name one difference between Q4_K and Q4_0 quantization."),
    ("q11", "Summarise the plot of Romeo and Juliet in one sentence."),
    ("q12", "State the boiling point of water at 1 atm in Celsius."),
]


def post(body, timeout=900):
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def collect(arm, reps=2):
    os.makedirs(OUTDIR, exist_ok=True)
    made = 0
    for pid, text in PROMPTS:
        for rep in range(reps):
            if os.path.exists(DUMP):
                os.remove(DUMP)
            body = {"model": "any", "messages": [{"role": "user", "content": text}],
                    "max_tokens": 1, "temperature": 0.0, "stream": False}
            t0 = time.time()
            out = post(body)
            dt = time.time() - t0
            if not os.path.exists(DUMP):
                print("  !! no dump for %s rep%d (engine without the env?)" % (pid, rep))
                continue
            dst = "%s/%s_%s_%d.bin" % (OUTDIR, arm, pid, rep)
            os.replace(DUMP, dst)
            n = os.path.getsize(dst) // 4
            made += 1
            tok = (out["choices"][0].get("message") or {}).get("content")
            print("  %-3s %-3s rep%d %5.2fs  vocab=%d  tok=%r" % (arm, pid, rep, dt, n, tok))
    print("wrote %d dumps" % made)


def load(path):
    with open(path, "rb") as f:
        raw = f.read()
    return list(struct.unpack("<%df" % (len(raw) // 4), raw))


def to_prob(v):
    mx = max(v)
    import math
    ws = [math.exp(x - mx) for x in v]
    z = sum(ws)
    return [w / z for w in ws]


def kl(p, q):
    import math
    tot = 0.0
    for a, b in zip(p, q):
        if a > 0.0:
            tot += a * math.log(a / max(b, 1e-30))
    return tot


def compare(arm_a, arm_b, reps=2):
    rows = []
    for pid, _ in PROMPTS:
        pa = os.path.join(OUTDIR, "%s_%s_0.bin" % (arm_a, pid))
        pb = os.path.join(OUTDIR, "%s_%s_0.bin" % (arm_b, pid))
        if not (os.path.exists(pa) and os.path.exists(pb)):
            continue
        p, q = to_prob(load(pa)), to_prob(load(pb))
        top_a = max(range(len(p)), key=p.__getitem__)
        top_b = max(range(len(q)), key=q.__getitem__)
        rows.append((pid, kl(p, q), kl(q, p), top_a == top_b))
    if not rows:
        print("no pairs")
        return
    import statistics
    ks = [r[1] for r in rows]
    print("A=%s vs B=%s  (%d prompts)" % (arm_a, arm_b, len(rows)))
    print("%-4s %10s %10s %s" % ("pid", "KL(A||B)", "KL(B||A)", "same_argmax"))
    for pid, ab, ba, same in rows:
        print("%-4s %10.6f %10.6f %s" % (pid, ab, ba, "yes" if same else "NO"))
    print("-" * 46)
    print("mean=%.6f  median=%.6f  max=%.6f  argmax_agree=%d/%d" %
          (sum(ks) / len(ks), statistics.median(ks), max(ks),
           sum(1 for r in rows if r[3]), len(rows)))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "collect":
        collect(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2)
    elif cmd == "compare":
        compare(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        raise SystemExit(2)
