#!/usr/bin/env python3
# W802d：CPU share 的 parity —— 贪心、足够长（避开 thinking 预算），落盘全文供跨臂逐字比对
import json, urllib.request, sys, hashlib
URL = "http://127.0.0.1:8090"
MODEL = "qwen3.8-flash-next-ud-iq4_xs-abliterated"
TAG = sys.argv[1] if len(sys.argv) > 1 else "X"
QS = [
    "用三句话说明为什么缓存命中率会随上下文变长而下降，最后给出一个具体数值例子。",
    "把下面四个数按升序排列并说明理由：17、4、9、23。",
]
out = []
for i, q in enumerate(QS):
    body = {"model": MODEL, "messages": [{"role": "user", "content": q}], "max_tokens": 320, "temperature": 0}
    req = urllib.request.Request(URL + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.loads(r.read().decode())
    c = d["choices"][0]
    txt = c["message"].get("content") or ""
    out.append(txt)
    print("PARITY %s q%d md5=%s len=%d finish=%s" % (TAG, i, hashlib.sha256(txt.encode()).hexdigest()[:16], len(txt),
                                                     c.get("finish_reason")), flush=True)
open("/home/albus/strata166/data/w802d_parity_%s.txt" % TAG, "w", encoding="utf-8").write("\n===\n".join(out))
