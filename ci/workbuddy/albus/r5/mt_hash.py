# -*- coding: utf-8 -*-
"""mt_hash.py —— 逐字口径的答案对照：同一批 prompt、temperature 0、固定 max_tokens，
把 content 的 sha256 打出来。用途：换了 PLE 取数模式（direct / mmap / ram）之后证明**答案没变**。

用法: mt_hash.py <port> <tag> [corpus] [max_tokens]
"""
import hashlib
import json
import sys
import time
import urllib.request

PORT = sys.argv[1] if len(sys.argv) > 1 else "8090"
TAG = sys.argv[2] if len(sys.argv) > 2 else "X"
CORPUS = sys.argv[3] if len(sys.argv) > 3 else "dec_corpus.json"
MAXT = int(sys.argv[4]) if len(sys.argv) > 4 else 200
MODEL = "qwen3.8-flash-next-ud-iq4_xs-abliterated"

doc = json.load(open(CORPUS, encoding="utf-8"))
for i, p in enumerate(doc["prompts"][:3]):
    body = {"model": MODEL, "messages": [{"role": "user", "content": p}],
            "max_tokens": MAXT, "temperature": 0.0, "top_p": 1.0, "reasoning_effort": "none"}
    req = urllib.request.Request("http://127.0.0.1:%s/v1/chat/completions" % PORT,
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        j = json.loads(r.read().decode())
    txt = j["choices"][0]["message"].get("content") or ""
    u = j.get("usage", {})
    print("  H%-2d %s n=%d ptok=%s otok=%s wall=%.1fs" % (
        i, hashlib.sha256(txt.encode()).hexdigest()[:32], len(txt),
        u.get("prompt_tokens"), u.get("completion_tokens"), time.time() - t0), flush=True)
print("HASH_DONE " + TAG)
