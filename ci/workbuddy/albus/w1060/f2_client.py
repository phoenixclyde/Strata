#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1060 F2 client: 3-turn conversation with retry-on-503 (engine respawn after GPU fatal),
# reading prompt-cache reuse before/after the injected fatal. R79's session-integrity probe.
import json
import sys
import time
import urllib.error
import urllib.request

PORT = int(sys.argv[1])
TAG = sys.argv[2]
OUT = sys.argv[3]


def post(messages, max_tokens=24, retries=4):
    body = {"model": "default-big", "messages": messages, "max_tokens": max_tokens,
            "temperature": 0.0}
    for att in range(retries):
        try:
            req = urllib.request.Request("http://127.0.0.1:%d/v1/chat/completions" % PORT,
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=600) as r:
                j = json.loads(r.read())
            u = j.get("usage", {}) or {}
            return {"ok": True, "att": att, "wall_s": round(time.time() - t0, 2),
                    "prompt_tokens": u.get("prompt_tokens"),
                    "reused": u.get("reused_tokens", u.get("reused")),
                    "text": (j["choices"][0]["message"].get("content") or "")[:60]}
        except urllib.error.HTTPError as e:
            print("  HTTP %s att %d (engine respawn expected after fatal)" % (e.code, att), flush=True)
            time.sleep(3)
        except Exception as e:
            print("  ERR %s att %d" % (e, att), flush=True)
            time.sleep(3)
    return {"ok": False}


long_p = "Context paragraph. " + ("The quick brown fox jumps over the lazy dog. " * 120)
recs = []
m = [{"role": "user", "content": long_p + "\n\nQ: What is 2+2? One word."}]
r1 = post(m); recs.append(("t1", r1)); print("t1", r1, flush=True)
m += [{"role": "assistant", "content": r1.get("text", "4")},
      {"role": "user", "content": "Q: And 3+3? One word."}]
r2 = post(m); recs.append(("t2", r2)); print("t2", r2, flush=True)
m += [{"role": "assistant", "content": r2.get("text", "6")},
      {"role": "user", "content": "Q: And 4+4? One word."}]
r3 = post(m); recs.append(("t3", r3)); print("t3", r3, flush=True)
json.dump({"tag": TAG, "recs": recs}, open(OUT, "w"), indent=1, default=str)
print("F2_DONE", OUT)
