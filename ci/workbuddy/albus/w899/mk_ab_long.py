#!/usr/bin/env python3
"""R54 A/B long-output probe: greedy, ~200 tokens each, prints text + sha256.

A 48-token probe with two empty answers proved nothing.  A 200-token greedy continuation exercises
every GDN layer many times, so a layout/aliasing mistake in the fused chain would change the text.
"""
import hashlib
import json
import sys
import urllib.request

URL = "http://127.0.0.1:8090/v1/chat/completions"
PROMPTS = [
    "Write a 150-word description of how a lighthouse keeper spends a stormy night. Plain prose.",
    "Explain in 150 words why the sky is blue, then give one counterexample to the simplest explanation.",
]
MAXTOK = 200


def ask(prompt: str) -> str:
    body = json.dumps({
        "model": "x",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAXTOK,
        "temperature": 0,
        "stream": True,
    }).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    out = []
    with urllib.request.urlopen(req, timeout=1800) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            for ch in obj.get("choices", []):
                d = ch.get("delta") or {}
                piece = d.get("content") or d.get("reasoning_content") or ""   # a thinking model streams
                if piece:                                                    # the long part as reasoning
                    out.append(piece)
    return "".join(out)


def main() -> int:
    total = hashlib.sha256()
    for i, p in enumerate(PROMPTS, 1):
        t = ask(p)
        h = hashlib.sha256(t.encode()).hexdigest()[:16]
        total.update(t.encode())
        print("p%d sha %s len %4d  head: %s" % (i, h, len(t), t[:70].replace("\n", " ")))
    print("TOTAL", total.hexdigest()[:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
