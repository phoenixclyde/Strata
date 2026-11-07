import json, time, urllib.request, random, string

URL = "http://127.0.0.1:8090"
FILLER = "The quick brown fox jumps over the lazy dog. "

def make(n_sent, salt):
    return (salt + " ") + FILLER * n_sent

def post(text):
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": text}],
                       "max_tokens": 1, "temperature": 0.0, "stream": False}).encode()
    req = urllib.request.Request(URL + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        r = json.load(urllib.request.urlopen(req, timeout=300))
        return time.time() - t0, r.get("usage", {})
    except Exception as e:
        return time.time() - t0, {"error": str(e)}

# two DIFFERENT prompts of the same size, back to back: if the 2nd is much faster, warmth is the cause
for i, salt in enumerate(["alpha", "beta", "gamma"]):
    text = make(230, salt)
    dt, u = post(text)
    print("call %d: %.2fs  usage=%s" % (i + 1, dt, u))
    time.sleep(2)
