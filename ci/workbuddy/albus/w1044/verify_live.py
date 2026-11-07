#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zero-downtime in-production check: does the DP4A switch actually change the
attention phase now that attn is installed? Reads ONLY the new log slice."""
import io
import json
import re
import time
import urllib.request

LOG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log"
words = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike "
         "november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu").split()
start = io.open(LOG, encoding="utf-8", errors="replace").read().count("\n")
# ~8000 tokens: W1042 used 2200 words ~= 2.5K tokens; scale linearly-ish
text = " ".join(words[i % len(words)] for i in range(7000)) + " [" + str(int(time.time())) + "]"
body = json.dumps({"model": "x", "messages": [{"role": "user", "content": text}],
                   "max_tokens": 1, "temperature": 0.0}).encode()
req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body,
                             headers={"Content-Type": "application/json"})
t0 = time.time()
d = json.loads(urllib.request.urlopen(req, timeout=600).read())
u = d.get("usage") or {}
print("request: prompt_tokens=%s cached=%s wall=%.1fs" %
      (u.get("prompt_tokens"), (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
       time.time() - t0))
lines = io.open(LOG, encoding="utf-8", errors="replace").read().splitlines()[start:]
hits = [l for l in lines if "strata prefill timing:" in l and "qsa attn" in l]
for l in hits[-3:]:
    m = re.search(r"(\d+) tokens, GPU timeline (\d+) ms.*?qsa attn (\d+) \(([\d.]+)%\)", l, re.S)
    print("timing:", (m.group(1), m.group(2), m.group(3), m.group(4)) if m else l[:200])
print("new lines:", len(lines), "| prefill timing lines:", len(hits))
