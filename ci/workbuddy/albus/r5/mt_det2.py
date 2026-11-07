# -*- coding: utf-8 -*-
"""mt_det2.py —— 不可复现的**幅度**：同一 prompt 连发 N 次，算两两的公共前缀。

用法: mt_det2.py <port> <tag> [corpus] [idx] [reps] [max_tokens]
输出：每次的 sha256/长度，以及所有两两的公共前缀字符数（越接近 max_tokens*CPT 越无害）。
"""
import hashlib
import itertools
import json
import sys
import time
import urllib.request

PORT = sys.argv[1] if len(sys.argv) > 1 else "8090"
TAG = sys.argv[2] if len(sys.argv) > 2 else "X"
CORPUS = sys.argv[3] if len(sys.argv) > 3 else "dec_corpus.json"
IDX = int(sys.argv[4]) if len(sys.argv) > 4 else 0
REPS = int(sys.argv[5]) if len(sys.argv) > 5 else 4
MAXT = int(sys.argv[6]) if len(sys.argv) > 6 else 96
MODEL = "qwen3.8-flash-next-ud-iq4_xs-abliterated"

doc = json.load(open(CORPUS, encoding="utf-8"))
p = doc["prompts"][IDX]
outs = []
for i in range(REPS):
    body = {"model": MODEL, "messages": [{"role": "user", "content": p}],
            "max_tokens": MAXT, "temperature": 0.0, "top_p": 1.0, "reasoning_effort": "none"}
    req = urllib.request.Request("http://127.0.0.1:%s/v1/chat/completions" % PORT,
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        j = json.loads(r.read().decode())
    txt = j["choices"][0]["message"].get("content") or ""
    outs.append(txt)
    print("  R%d %s n=%d wall=%.1fs" % (i, hashlib.sha256(txt.encode()).hexdigest()[:32], len(txt),
                                        time.time() - t0), flush=True)


def cp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


print("  PREFIX matrix (chars):")
for i, j in itertools.combinations(range(REPS), 2):
    print("    R%d-R%d common=%d of min(%d,%d)" % (i, j, cp(outs[i], outs[j]),
                                                    len(outs[i]), len(outs[j])))
uniq = len({hashlib.sha256(t.encode()).hexdigest() for t in outs})
print("DET2 tag=%s reps=%d unique=%d maxt=%d" % (TAG, REPS, uniq, MAXT), flush=True)
