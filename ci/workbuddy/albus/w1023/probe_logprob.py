import json, time, urllib.request, sys
p = " ".join(["alpha bravo charlie delta echo foxtrot golf hotel india juliet"] * 40)[:4000]
body = json.dumps({"model": "x", "messages": [{"role": "user", "content": p}],
                   "max_tokens": 1, "temperature": 0.0, "logprobs": True, "top_logprobs": 3}).encode()
r = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body,
                           headers={"Content-Type": "application/json"})
t0 = time.perf_counter()
d = json.loads(urllib.request.urlopen(r, timeout=300).read())
dt = time.perf_counter() - t0
ch = d["choices"][0]
print("prompt_tokens", d.get("usage", {}).get("prompt_tokens"), "wall %.2fs" % dt)
print("logprobs present:", "logprobs" in ch and ch["logprobs"] is not None)
if ch.get("logprobs"):
    c = ch["logprobs"]["content"][0]
    print("token", repr(c.get("token")), "logprob", c.get("logprob"))
    print("top:", [(t["token"], round(t["logprob"], 4)) for t in c.get("top_logprobs", [])])
