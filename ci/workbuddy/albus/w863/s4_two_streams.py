#!/usr/bin/env python3
"""W863: is a second concurrent request queued?  Two requests, timed."""
import json
import threading
import time
import urllib.request

URL = "http://127.0.0.1:8090/v1/chat/completions"
MODEL = "qwen3.8-flash-next-ud-q4_k_xl-abliterated"
PROMPT = ("在远程测试台上，我们把显存的每一兆字节都算过一遍。请就这个话题写一段较长的说明，"
          "要求逐句展开，不要总结。")
res = {}


def one(tag, delay):
    time.sleep(delay)
    body = {"model": MODEL, "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": 96, "temperature": 0}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=1200) as r:
            d = json.loads(r.read())
        res[tag] = (t0, time.time(), d.get("usage", {}).get("completion_tokens"))
    except Exception as e:
        res[tag] = (t0, time.time(), "FAIL %r" % e)


ts = [threading.Thread(target=one, args=("A", 0.0)), threading.Thread(target=one, args=("B", 1.0))]
for t in ts:
    t.start()
for t in ts:
    t.join()
base = min(v[0] for v in res.values())
for k in sorted(res):
    t0, t1, n = res[k]
    print("%s: sent +%.2fs, first-byte..end %.2fs, tokens=%s" % (k, t0 - base, t1 - t0, n))
