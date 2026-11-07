#!/usr/bin/env python3
"""W1036 / A0 A/B: measure one arm of the dp4a port and write a JSON summary.

Runs on 166.  Assumes the engine is up on 127.0.0.1:8090 and that the arm's binary is the one installed.
The prompts are seeded per (length, index) so BOTH arms see the same text; each arm starts from a cold
engine (the container is restarted between arms), and within an arm every index uses a different seed, so
no request is served from the prompt cache.

  python3 ab_a0.py <out.json> <label>
"""
import json
import os
import random
import re
import statistics as st
import sys
import time
import urllib.request

LOG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log"
URL = "http://127.0.0.1:8090/v1/chat/completions"
V = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa "
     "quebec romeo sierra tango uniform victor whiskey xray yankee zulu amber basalt cobalt dune ember "
     "fjord garnet harbor indigo jasper kelp lagoon marrow nectar onyx prism quartz rivet summit tundra "
     "umber vapor willow xenon yarrow zephyr").split()

PRE = [(2500, 3), (8000, 2)]     # (tokens, repeats)
SALT_FILE = "/home/albus/strata166/tmp/w1036/a0_salt"


def salt():
    """One value per window, written by the driver BEFORE the first arm: both arms then see byte-identical
    prompts, and a later window never re-uses the previous window's prompt-cache entries."""
    try:
        with open(SALT_FILE, "r", encoding="utf-8") as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return 0

DEC = 5                          # decode requests, 128 tokens each


def log_off():
    try:
        return os.path.getsize(LOG)
    except OSError:
        return 0


def read_new(off):
    try:
        with open(LOG, "r", errors="replace") as fh:
            fh.seek(off)
            return fh.read()
    except OSError:
        return ""


def ask(prompt, max_tokens, timeout=300):
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens, "temperature": 0.0}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    d = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    return d, time.time() - t0


def main():
    out, label = sys.argv[1], sys.argv[2]
    res = {"label": label, "prefill": [], "decode": []}
    # warm-up: a freshly started engine does not always write the timing line for its first request
    try:
        ask("warm up alpha bravo charlie delta echo foxtrot", 4, timeout=120)
        time.sleep(1.0)
        print("warm-up done", flush=True)
    except Exception as exc:                      # noqa: BLE001 - a warm-up must never abort the arm
        print("warm-up ignored:", type(exc).__name__, flush=True)
    for ntok, reps in PRE:
        for i in range(reps):
            rng = random.Random(salt() + 90000 + ntok * 7 + i)   # same seed in both arms, new salt each window
            prompt = " ".join(rng.choice(V) for _ in range(int(ntok * 0.82)))
            off = log_off()
            m = []
            for attempt in range(3):
                d, wall = ask(prompt, 2)
                time.sleep(0.3)
                new = read_new(off)
                m = re.findall(r"strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms, wall (\d+) ms", new)
                if m:
                    break
                ct = (d.get("usage", {}).get("prompt_tokens_details") or {}).get("cached_tokens", 0)
                if ct and d.get("usage", {}).get("prompt_tokens") and ct >= d["usage"]["prompt_tokens"] - 1:
                    raise SystemExit("prompt was served from cache (cached=%d) - salt did not take" % ct)
                off = log_off()                      # the line may simply not have been flushed yet
                print("  retry %d for %d/%d" % (attempt + 1, ntok, i), flush=True)
                time.sleep(2.0)
            if not m:
                raise SystemExit("no prefill timing line for %d/%d after 3 tries" % (ntok, i))
            tk, gpu, wl = (int(x) for x in m[-1])
            res["prefill"].append({"target": ntok, "tokens": tk, "gpu_ms": gpu, "wall_ms": wl,
                                   "http_s": round(wall, 3)})
            print("prefill %5d -> tokens=%d wall=%d ms  (http %.2fs)" % (ntok, tk, wl, wall), flush=True)
    for i in range(DEC):
        rng = random.Random(salt() + 70000 + i)
        prompt = " ".join(rng.choice(V) for _ in range(40))
        off = log_off()
        d, wall = ask(prompt, 128)
        time.sleep(0.25)
        new = read_new(off)
        # three independent readings of the same decode, all from the engine's own log
        sv = re.findall(r"strata serve: prompt (\d+) tokens .*? (\d+) generated in (\d+) ms \(([\d.]+) tok/s\)", new)
        dw = re.findall(r"strata decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window", new)
        for attempt in range(3):
            if sv:
                break
            off = log_off()
            d, wall = ask(prompt, 128)
            time.sleep(0.3)
            new = read_new(off)
            sv = re.findall(r"strata serve: prompt (\d+) tokens .*? (\d+) generated in (\d+) ms \(([\d.]+) tok/s\)", new)
            dw = re.findall(r"strata decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window", new)
            if not sv:
                print("  retry %d for decode %d" % (attempt + 1, i), flush=True)
                time.sleep(2.0)
        if not sv:
            raise SystemExit("no serve line for decode %d after 3 tries" % i)
        gen = int(sv[-1][1]); ms = int(sv[-1][2]); rate = float(sv[-1][3])
        rec = {"generated": gen, "gen_ms": ms, "tok_s": rate, "http_s": round(wall, 3)}
        if dw:
            rec.update({"windows": int(dw[-1][0]), "tokens_per_window": float(dw[-1][2]),
                        "ms_per_window": float(dw[-1][3])})
        res["decode"].append(rec)
        print("decode %d -> %d tok in %d ms = %.1f tok/s%s" % (
            i, gen, ms, rate,
            ("  %.2f ms/window (%d windows)" % (rec["ms_per_window"], rec["windows"])) if dw else ""), flush=True)

    # per-target prefill summary (ms per 1k tokens), so a length mix cannot hide a change
    for ntok, _ in PRE:
        v = [r for r in res["prefill"] if r["target"] == ntok]
        if not v:
            continue
        wl = [r["wall_ms"] for r in v]
        per = [r["wall_ms"] * 1000.0 / r["tokens"] for r in v]
        res["prefill_summary_%d" % ntok] = {
            "n": len(v), "wall_ms": round(st.mean(wl), 1),
            "us_per_tok": round(st.mean(per), 1),
            "cv_pct": round(100 * st.stdev(per) / st.mean(per), 1) if len(per) > 1 else 0.0}
    r = [x["tok_s"] for x in res["decode"]]
    res["decode_summary"] = {"n": len(r), "tok_s": round(st.mean(r), 2),
                             "cv_pct": round(100 * st.stdev(r) / st.mean(r), 1) if len(r) > 1 else 0.0,
                             "min": round(min(r), 1), "max": round(max(r), 1)}
    mw = [x["ms_per_window"] for x in res["decode"] if "ms_per_window" in x]
    if mw:
        res["decode_summary"]["ms_per_window"] = round(st.mean(mw), 2)
        res["decode_summary"]["cv_ms_per_window"] = round(100 * st.stdev(mw) / st.mean(mw), 1) if len(mw) > 1 else 0.0
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print("WROTE", out)


if __name__ == "__main__":
    main()
