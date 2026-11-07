import json, sys, time, urllib.request, os
LABEL = sys.argv[1]
EN = ("The quick brown fox jumps over the lazy dog. " * 90)
ZH = ("量化推理的性能取决于内存带宽与内核调度，而专家混合模型还要额外处理路由与权重换入换出。" * 60)
CASES = [("en2k", EN + "\n\nQuestion: what animal appears in the text above? Answer in three words."),
         ("zh2k", ZH + "\n\n问题：上面这段话主要讲什么？用一句话回答。")]
out = {"label": LABEL, "cases": {}}
for name, p in CASES:
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": p}],
                       "max_tokens": 256, "temperature": 0.0}).encode()
    r = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body,
                               headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    d = json.loads(urllib.request.urlopen(r, timeout=900).read())
    dt = time.perf_counter() - t0
    m = d["choices"][0].get("message") or {}
    out["cases"][name] = {"content": m.get("content") or "", "reasoning": m.get("reasoning_content") or "",
                          "usage": d.get("usage"), "wall_s": round(dt, 2)}
    print("%-5s ctok=%s %.1fs content=%d reasoning=%d" % (name, (d.get("usage") or {}).get("completion_tokens"),
                                                          dt, len(out["cases"][name]["content"]),
                                                          len(out["cases"][name]["reasoning"])))
d = "/home/albus/strata166/ci/state/cfg"
os.makedirs(d, exist_ok=True)
json.dump(out, open(os.path.join(d, "longfp_%s.json" % LABEL), "w"), ensure_ascii=False, indent=1)
print("saved", os.path.join(d, "longfp_%s.json" % LABEL))
