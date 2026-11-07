#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W808 解码 tok/s 客户端：三条不同的 prompt，各生成 N token（temperature 0），
   从服务端 /metrics 的逐请求记录里取 decode_ms 与 output_tokens（不含客户端开销）。
   用法：mt_gen.py <port> <tag> <out.json> <corpus.json> [max_tokens] [n_prompts]
"""
import json, sys, time, urllib.request

port = sys.argv[1] if len(sys.argv) > 1 else "8090"
tag = sys.argv[2] if len(sys.argv) > 2 else "X"
outp = sys.argv[3] if len(sys.argv) > 3 else "/tmp/gen_%s.json" % tag
corpus = sys.argv[4] if len(sys.argv) > 4 else "dec_corpus.json"
MAXT = int(sys.argv[5]) if len(sys.argv) > 5 else 200
NP = int(sys.argv[6]) if len(sys.argv) > 6 else 3
MODEL = "qwen3.8-flash-next-ud-iq4_xs-abliterated"


def post(body, timeout=900):
    req = urllib.request.Request("http://127.0.0.1:%s/v1/chat/completions" % port,
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def metric0():
    with urllib.request.urlopen("http://127.0.0.1:%s/metrics" % port, timeout=10) as r:
        m = json.loads(r.read().decode())
    rs = m.get("requests") or []
    return rs[0] if rs else {}


doc = json.load(open(corpus, encoding="utf-8"))
res = []
for i in range(NP):
    p = doc["prompts"][i]
    body = {"model": MODEL, "messages": [{"role": "user", "content": p}],
            "max_tokens": MAXT, "temperature": 0.0, "top_p": 1.0, "reasoning_effort": "none"}
    t0 = time.time()
    try:
        j = post(body)
        wall = time.time() - t0
        time.sleep(0.3)
        m = metric0()
        dec = m.get("decode_ms")
        out = m.get("output_tokens")
        tps = (1000.0 * out / dec) if (dec and out) else None
        res.append({"i": i, "ok": True, "wall_s": round(wall, 2),
                    "prompt_ms": m.get("prompt_ms"), "decode_ms": dec, "output_tokens": out,
                    "decode_tps": round(tps, 2) if tps else None,
                    "finish": j["choices"][0].get("finish_reason")})
        print("  p%-2d ptok=%-4s out=%-4s decode=%-7s ms  %s tok/s  wall=%.1fs" %
              (i, m.get("prompt_tokens"), out, dec, ("%.1f" % tps) if tps else "-", wall))
    except Exception as ex:
        res.append({"i": i, "ok": False, "err": repr(ex)[:160]})
        print("  p%-2d ERROR %r" % (i, ex))

ok = [r for r in res if r.get("ok") and r.get("decode_tps")]
if ok:
    print("  MEDIAN decode_tps = %.2f  (n=%d)" % (sorted(r["decode_tps"] for r in ok)[len(ok) // 2], len(ok)))
json.dump({"tag": tag, "max_tokens": MAXT, "results": res}, open(outp, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("WROTE", outp)
