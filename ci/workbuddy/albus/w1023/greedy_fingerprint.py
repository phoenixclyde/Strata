#!/usr/bin/env python3
"""Greedy-output fingerprint: the cheapest real check that the new ggml computes the same thing.

serve/server.py does not fill logprobs (content is always empty), so the only observable
of the prefill's numerics is what the decoder then produces.  Temperature 0 + fixed
prompts + 48 tokens: identical text means the prefill path agrees, a divergence means the
MoE layout / Q8_1 correction really did change the numbers and must be judged, not ignored.

Usage: greedy_fingerprint.py <label>
Writes /home/albus/strata166/ci/state/cfg/greedy_<label>.json
"""
import json, sys, time, urllib.request, os

LABEL = sys.argv[1] if len(sys.argv) > 1 else "x"
EN = ("The quick brown fox jumps over the lazy dog. " * 90)
ZH = ("量化推理的性能取决于内存带宽与内核调度，而专家混合模型还要额外处理路由与权重换入换出。" * 60)
PROMPTS = [
    ("short", "Explain in one sentence why the sky is blue."),
    ("en2k", EN + "\n\nQuestion: what animal appears in the text above? Answer in three words."),
    ("zh2k", ZH + "\n\n问题：上面这段话主要讲什么？用一句话回答。"),
]

out = {"label": LABEL, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "cases": {}}
for name, p in PROMPTS:
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": p}],
                       "max_tokens": 48, "temperature": 0.0}).encode()
    r = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body,
                               headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    d = json.loads(urllib.request.urlopen(r, timeout=600).read())
    dt = time.perf_counter() - t0
    u = d.get("usage", {})
    msg = d["choices"][0].get("message") or {}
    txt = msg.get("content") or msg.get("reasoning_content") or ""
    out["cases"][name] = {"prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
                          "wall_s": round(dt, 3), "text": txt}
    print("%-6s ptok=%-5s ctok=%-3s %.2fs | %s" % (name, u.get("prompt_tokens"), u.get("completion_tokens"),
                                                   dt, (txt or "(empty)")[:70].replace("\n", " ")))

d = "/home/albus/strata166/ci/state/cfg"
os.makedirs(d, exist_ok=True)
path = os.path.join(d, "greedy_%s.json" % LABEL)
json.dump(out, open(path, "w"), ensure_ascii=False, indent=1)
print("saved", path)
