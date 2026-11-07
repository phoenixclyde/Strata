#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1042: the task-level gate for the attention OPT (R104's needle, two depths).

  python3 needle1042.py <tag>        # reads/writes on the host, engine on 127.0.0.1:8090
Prints one line per depth and a JSON blob; a growth (kv-grow) is live in the production config, so the 28K
prompt also re-exercises the elastic K/V path.
"""
import json
import random
import sys
import time
import urllib.request

CODE = "XK-4471-QN"
V = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa "
     "quebec romeo sierra tango uniform victor whiskey xray yankee zulu amber basalt cobalt dune ember "
     "fjord garnet harbor indigo jasper kelp lagoon marrow nectar onyx prism quartz rivet summit tundra "
     "umber vapor willow").split()


def build(nwords, salt):
    rng = random.Random(20261107)
    body = " ".join(rng.choice(V) for _ in range(nwords))
    return ("The access code for the vault is " + CODE + " . Remember it.\n\n" + body +
            "\n\nQuestion: what is the access code for the vault? Answer with the code only. [" + salt + "]")


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "run"
    out = {}
    for nwords, label in ((10000, "16K"), (18000, "28K")):
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
        out[label] = {"hit": CODE in ans, "prompt_tokens": u.get("prompt_tokens"),
                      "cached": (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
                      "secs": round(time.time() - t0, 1), "tail": ans[-60:]}
        print("%s %-4s hit=%s prompt=%s cached=%s %.1fs" % (tag, label, out[label]["hit"],
                                                           out[label]["prompt_tokens"], out[label]["cached"],
                                                           out[label]["secs"]), flush=True)
    print("JSON " + json.dumps({tag: out}))


if __name__ == "__main__":
    main()
