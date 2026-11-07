#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Long-context needle GRID for the R103 install gate (W1043, NOT EXECUTED).

Runs inside the 166 host against a TEMP server on :8090 that the window script
starts with the right arm (off = production kvg, on = attn + ATTN_DP4A=1).
Both arms use cfgP_*.json with --kv-grow (verified W1043).

Spec: albus/w1043/LONGCTX_GATE.md §3/§4.  Grid = lengths x depths, each point
has its own salt so cached_tokens MUST be 0; a cached point is DISCARDED.

    python3 longctx_needle.py --label off --out /w/grid_off.json
    python3 longctx_needle.py --label on  --out /w/grid_on.json
    python3 longctx_needle.py --self-test     # no GPU, no server, checks the grid builder
"""
import argparse
import io
import json
import random
import time
import urllib.request

CODE = "XK-4471-QN"
V = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa "
     "quebec romeo sierra tango uniform victor whiskey xray yankee zulu amber basalt cobalt dune ember "
     "fjord garnet harbor indigo jasper kelp lagoon marrow nectar onyx prism quartz rivet summit tundra "
     "umber vapor willow").split()
URL = "http://127.0.0.1:8090/v1/chat/completions"


def build(nwords, depth_pct, salt):
    """Put the needle at depth_pct of the haystack, question at the end."""
    rng = random.Random(20261107 + nwords + depth_pct)
    words = [rng.choice(V) for _ in range(nwords)]
    needle = "The access code for the vault is %s . Remember it." % CODE
    pos = int(len(words) * depth_pct / 100.0)
    words.insert(pos, needle)
    return (" ".join(words) + "\n\nQuestion: what is the access code for the vault? "
            "Answer with the code only. [%s]" % salt)


def one(nwords, depth_pct, salt, timeout):
    prompt = build(nwords, depth_pct, salt)
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 200, "temperature": 0.0}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    d = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    m = d["choices"][0]["message"]
    ans = (m.get("content") or "") + " || " + (m.get("reasoning_content") or "")
    u = d.get("usage") or {}
    pd = u.get("prompt_tokens_details") or {}
    return {"hit": CODE in ans, "prompt_tokens": u.get("prompt_tokens"),
            "cached": pd.get("cached_tokens", 0), "secs": round(time.time() - t0, 1),
            "finish": d["choices"][0].get("finish_reason"), "answer": ans[-160:]}


def self_test():
    bad = 0
    for n in (16000, 32000, 64000):
        for dep in (0, 50, 100):
            p = build(n, dep, "selftest")
            words = p.split(" ")
            idx = next(i for i, w in enumerate(words) if w == "The")
            frac = idx / float(len(words))
            want = dep / 100.0
            ok = abs(frac - want) < 0.02 and CODE in p and p.rstrip().endswith("]")
            bad += 0 if ok else 1
            print("  n=%-6d depth=%3d%%  needle_at=%.3f %s" % (n, dep, frac, "OK" if ok else "BAD"))
    print("LONGCTX_NEEDLE_SELF_TEST: %d/%d" % (9 - bad, 9))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="off")
    ap.add_argument("--out", required=False)
    ap.add_argument("--lengths", default="16000,32000,64000")
    ap.add_argument("--depths", default="0,50,100")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    lengths = [int(x) for x in a.lengths.split(",")]
    depths = [int(x) for x in a.depths.split(",")]
    out = {"label": a.label, "code": CODE, "grid": {}, "invalid": []}
    for n in lengths:
        for dep in depths:
            # W1042 measured 2200 words ~= 2.5K tokens, 18000 words ~= 21K tokens
            # => ~0.86 words/token.  Rounded; the REAL prompt_tokens is recorded.
            nwords = int(n / 1.6)
            key = "%d@%d%%" % (n, dep)
            salt = "%s-%d-%d-%d" % (a.label, n, dep, int(time.time() * 1000))
            r = one(nwords, dep, salt, a.timeout)
            r["nwords"] = nwords
            r["salt"] = salt
            if r["cached"]:
                out["invalid"].append(key + " cached_tokens=%s" % r["cached"])
            out["grid"][key] = r
            print("%s %-12s hit=%s tok=%s cached=%s %ss" %
                  (a.label, key, r["hit"], r["prompt_tokens"], r["cached"], r["secs"]), flush=True)
    if a.out:
        io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("SUMMARY label=%s hits=%d/%d invalid=%d" %
          (a.label, sum(1 for v in out["grid"].values() if v["hit"]), len(out["grid"]), len(out["invalid"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
