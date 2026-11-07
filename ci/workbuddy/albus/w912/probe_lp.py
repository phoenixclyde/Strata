#!/usr/bin/env python3
"""W912/R59 probe: does the production server return per-token logprobs, and in what shape?

Sends one small greedy chat completion with logprobs=true, top_logprobs=20 and prints the raw
structure (trimmed) so the collector can be written against facts, not guesses.
"""
import json
import urllib.request

URL = "http://127.0.0.1:8090/v1/chat/completions"
BODY = {
    "model": "any",
    "messages": [{"role": "user", "content": "Reply with exactly: A B C D E F G H"}],
    "max_tokens": 32,
    "temperature": 0.0,
    "logprobs": True,
    "top_logprobs": 20,
    "stream": False,
}


def post(url, body, timeout=600):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


if __name__ == "__main__":
    out = post(URL, BODY)
    print("top-level keys:", sorted(out.keys()))
    ch = out["choices"][0]
    print("choice keys:", sorted(ch.keys()))
    print("finish_reason:", ch.get("finish_reason"), "| text:", repr(ch.get("message", {}).get("content", ""))[:80])
    lp = ch.get("logprobs")
    if not lp:
        print("NO LOGPROBS RETURNED ->", json.dumps(ch)[:400])
        raise SystemExit(1)
    print("logprobs keys:", sorted(lp.keys()))
    for key in ("content", "reasoning_content"):
        arr = lp.get(key) or []
        print("  %-18s entries=%d" % (key, len(arr)))
    content = (lp.get("content") or lp.get("reasoning_content") or [])
    print("tokens with logprobs:", len(content))
    if content:
        item = content[0]
        print("first item keys:", sorted(item.keys()))
        top = item.get("top_logprobs") or []
        print("first item token=%r logprob=%s top_n=%d" % (item.get("token"), item.get("logprob"), len(top)))
        for t in top[:5]:
            print("   ", t)
