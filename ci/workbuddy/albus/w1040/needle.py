#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1040: the 20K needle test (functional check of the elastic K/V growth path).

A code is planted in the first sentence, ~18000 words of filler follow, then the question.  A growth has to keep
the cells mapped at the start while it appends more; if it corrupts them the answer dies.  Greedy, and a salt at
the very end keeps the prompt cache from serving the same prompt twice.

  python needle.py before|after
"""
import io, json, os, sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

TAG = sys.argv[1] if len(sys.argv) > 1 else "run"
WORDS = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa "
         "quebec romeo sierra tango uniform victor whiskey xray yankee zulu amber basalt cobalt dune ember "
         "fjord garnet harbor indigo jasper kelp lagoon marrow nectar onyx prism quartz rivet summit tundra "
         "umber vapor willow")

S = r'''
import json, random, time, urllib.request
CODE = "XK-4471-QN"
V = "__WORDS__".split()
def build(nwords, salt):
    rng = random.Random(20261107)
    body = " ".join(rng.choice(V) for _ in range(nwords))
    return ("The access code for the vault is " + CODE + " . Remember it." + chr(10) + chr(10) + body +
            chr(10) + chr(10) + "Question: what is the access code for the vault? Answer with the code only. [" +
            salt + "]")
out = {}
for nwords, label in ((2200, "2.5K"), (18000, "21K")):
    prompt = build(nwords, str(int(time.time())))
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 24, "temperature": 0.0}).encode()
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    d = json.loads(urllib.request.urlopen(req, timeout=900).read())
    u = d.get("usage") or {}
    pd = u.get("prompt_tokens_details") or {}
    ans = d["choices"][0]["message"]["content"]
    out[label] = {"answer": ans, "prompt_tokens": u.get("prompt_tokens"),
                  "cached": pd.get("cached_tokens", 0), "secs": round(time.time() - t0, 1),
                  "hit": CODE in ans}
print(json.dumps(out))
'''.replace("__WORDS__", WORDS)

rc, out, err = _sshutil.run_remote(S, timeout=900)
print("rc=", rc)
if err.strip():
    print("STDERR:", err[-800:])
line = [l for l in (out or "").strip().splitlines() if l.startswith("{")]
d = json.loads(line[-1]) if line else {}
path = os.path.join(r"D:/workbuddy_space/strata_ws/albus/w1040", "needle_%s.json" % TAG)
io.open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1))
for k, v in d.items():
    print("%-4s hit=%s prompt=%s cached=%s %ss  %r" % (k, v["hit"], v["prompt_tokens"], v["cached"],
                                                       v["secs"], v["answer"][:50]))
print("wrote", path)
