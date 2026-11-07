#!/usr/bin/env python3
"""R54 A/B text probe: greedy, fixed prompts, prints the text and its sha256.

Used to catch a barrier starved persistent kernel: a wrong-but-fast arm would change the text.
"""
import hashlib
import json
import sys
import urllib.request

URL = "http://127.0.0.1:8090/v1/chat/completions"
PROMPTS = [
    "List the three smallest prime numbers, comma separated, nothing else.",
    "Write one sentence that contains exactly the word 'harbour'.",
    "What is 17 * 23? Answer with the number only.",
]


def ask(prompt: str, mx: int = 48) -> str:
    body = json.dumps({
        "model": "x",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": mx,
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
                if d.get("content"):
                    out.append(d["content"])
    return "".join(out)


def main() -> int:
    total = hashlib.sha256()
    for p in PROMPTS:
        t = ask(p)
        h = hashlib.sha256(t.encode()).hexdigest()[:16]
        total.update(t.encode())
        print("sha %s  len %3d  %s" % (h, len(t), t.replace("\n", " ")[:110]))
    print("TOTAL", total.hexdigest()[:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
