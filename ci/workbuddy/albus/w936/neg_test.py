#!/usr/bin/env python3
"""W936: an ordinary engine error must stay a 400 (bad request), not a 503, and must not end the engine."""
import json, time, urllib.request, urllib.error

URL = "http://127.0.0.1:8090/v1/chat/completions"


def call(tag, body, timeout=600):
    data = json.dumps(body).encode()
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            print("%-14s http=%d  %.1fs  ok" % (tag, r.status, time.time() - t0))
            return r.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        print("%-14s http=%d  %.1fs  BODY=%r" % (tag, e.code, time.time() - t0, raw[:220]))
        return e.code
    except Exception as e:
        print("%-14s EXC %.1fs %s %s" % (tag, time.time() - t0, type(e).__name__, str(e)[:120]))
        return None


base = {"model": "x", "messages": [{"role": "user", "content": "hi"}], "temperature": 0}

print("=== A. 超上下文（引擎应打 ERR 但不是 fatal）===")
b = dict(base)
b["max_tokens"] = 400000          # > max_context 262144
call("over-context", b)

print()
print("=== B. 紧接着正常请求：引擎应仍在（pid 不变、秒回）===")
b = dict(base)
b["max_tokens"] = 8
call("normal-after", b)

print()
print("=== C. 空 messages（非法请求）===")
call("empty-msgs", {"model": "x", "messages": [], "max_tokens": 4})
