import json, random, time, urllib.request
CODE = "XK-4471-QN"
V = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa "
     "quebec romeo sierra tango uniform victor whiskey xray yankee zulu amber basalt cobalt dune ember "
     "fjord garnet harbor indigo jasper kelp lagoon marrow nectar onyx prism quartz rivet summit tundra "
     "umber vapor willow").split()
def build(nwords, salt):
    rng = random.Random(20261107)
    body = " ".join(rng.choice(V) for _ in range(nwords))
    return ("The access code for the vault is " + CODE + " . Remember it." + chr(10) + chr(10) + body +
            chr(10) + chr(10) + "Question: what is the access code for the vault? Answer with the code only. [" + salt + "]")
out = {}
for nwords, label in ((2200, "2.5K"), (18000, "21K")):
    prompt = build(nwords, str(int(time.time())))
    b = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200, "temperature": 0.0}).encode()
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=b,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    d = json.loads(urllib.request.urlopen(req, timeout=900).read())
    m = d["choices"][0]["message"]
    ans = (m.get("content") or "") + " || " + (m.get("reasoning_content") or "")
    u = d.get("usage") or {}
    pd = u.get("prompt_tokens_details") or {}
    out[label] = {"answer": ans, "prompt_tokens": u.get("prompt_tokens"), "cached": pd.get("cached_tokens", 0),
                  "secs": round(time.time() - t0, 1), "hit": CODE in ans,
                  "finish": d["choices"][0].get("finish_reason")}
print(json.dumps(out))
