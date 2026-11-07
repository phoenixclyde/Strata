# -*- coding: utf-8 -*-
"""mt_det.py —— 复现性探针：同一个 prompt 连发 N 次，打印每次的 sha256 与长度。

用途：分辨「同一个引擎实例内是否确定」与「跨重启是否确定」。
真值（chunk / 借槽）从引擎 `STRATA_TRACE=1` 的 `trace:` 行取，本脚本只管答案指纹。

用法: mt_det.py <port> <tag> [corpus] [prompt_idx] [reps] [max_tokens]
"""
import hashlib
import json
import sys
import time
import urllib.request

PORT = sys.argv[1] if len(sys.argv) > 1 else "8090"
TAG = sys.argv[2] if len(sys.argv) > 2 else "X"
CORPUS = sys.argv[3] if len(sys.argv) > 3 else "dec_corpus.json"
IDX = int(sys.argv[4]) if len(sys.argv) > 4 else 0
REPS = int(sys.argv[5]) if len(sys.argv) > 5 else 3
MAXT = int(sys.argv[6]) if len(sys.argv) > 6 else 64
MODEL = "qwen3.8-flash-next-ud-iq4_xs-abliterated"

doc = json.load(open(CORPUS, encoding="utf-8"))
p = doc["prompts"][IDX]
hs = []
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
    h = hashlib.sha256(txt.encode()).hexdigest()[:32]
    hs.append(h)
    print("  R%d %s n=%d wall=%.1fs" % (i, h, len(txt), time.time() - t0), flush=True)
    time.sleep(0.4)
uniq = len(set(hs))
print("DET tag=%s reps=%d unique=%d %s" % (TAG, REPS, uniq, "SAME" if uniq == 1 else "DIFF"), flush=True)
