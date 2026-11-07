#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W807 解码侧质量仪器的客户端：每条 prompt 生成长文本（temperature 0），整段逐字存下来。
   与提示侧的区别：提示侧比 teacher-forced 分布（LOGPOS，只在 read_windows 落行）；这里比**贪心生成的整段输出**。
   用法：mt_decq.py <port> <tag> <out.json> <corpus.json> [max_tokens]
"""
import json, sys, time, urllib.request

port = sys.argv[1] if len(sys.argv) > 1 else "8090"
tag = sys.argv[2] if len(sys.argv) > 2 else "X"
outp = sys.argv[3] if len(sys.argv) > 3 else "/tmp/decq_%s.json" % tag
corpus = sys.argv[4] if len(sys.argv) > 4 else "dec_corpus.json"
MAXT = int(sys.argv[5]) if len(sys.argv) > 5 else 600
MODEL = "qwen3.8-flash-next-ud-iq4_xs-abliterated"


def post(body, timeout=900):
    req = urllib.request.Request("http://127.0.0.1:%s/v1/chat/completions" % port,
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode()), time.time() - t0


doc = json.load(open(corpus, encoding="utf-8"))
res = []
for i, p in enumerate(doc["prompts"]):
    body = {"model": MODEL, "messages": [{"role": "user", "content": p}],
            "max_tokens": MAXT, "temperature": 0.0, "top_p": 1.0,
            "reasoning_effort": "none"}
    try:
        d, w = post(body)
        ch = d["choices"][0]
        txt = ch["message"].get("content") or ""
        rsn = ch["message"].get("reasoning_content") or ""
        u = d.get("usage") or {}
        res.append({"i": i, "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
                    "finish": ch.get("finish_reason"), "wall_s": round(w, 3),
                    "nchar": len(txt), "text": txt, "reasoning_len": len(rsn)})
        print("  p%-2d ptok=%-4s ctok=%-4s finish=%-6s %.1fs chars=%d" %
              (i, u.get("prompt_tokens"), u.get("completion_tokens"), ch.get("finish_reason"), w, len(txt)))
    except Exception as ex:
        res.append({"i": i, "error": repr(ex)[:200]})
        print("  p%-2d ERROR %r" % (i, ex))

json.dump({"tag": tag, "max_tokens": MAXT, "results": res}, open(outp, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("WROTE", outp)
