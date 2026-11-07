#!/usr/bin/env python3
"""W1037 / R103 arm measurement: one arm of the gfx906 port bundle, plus its prefill phase split.

Runs on 166 against 127.0.0.1:8090.  Same contract as w1036/ab_a0.py:
  * prompts are seeded from one salt written by the driver, so every arm of a window sees byte-identical text
    and a later window never re-uses this window's prompt-cache entries;
  * each arm starts from a freshly restarted engine (the driver restarts), so the first 2 requests are
    discarded by the engine's own warm-up behaviour (P200) and one extra warm-up request is sent here;
  * every number comes from the engine's own log line, not from HTTP wall time.

  python3 ab_w1037.py <out.json> <label>
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
SALT_FILE = "/home/albus/strata166/tmp/w1037/salt"
V = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa "
     "quebec romeo sierra tango uniform victor whiskey xray yankee zulu amber basalt cobalt dune ember "
     "fjord garnet harbor indigo jasper kelp lagoon marrow nectar onyx prism quartz rivet summit tundra "
     "umber vapor willow xenon yarrow zephyr").split()

PRE = [(2500, 3), (8000, 2)]     # (target tokens, repeats)
DEC = 3                          # decode requests, 128 tokens each (not a success criterion, only a "no worse" gate)
PHASE_RE = re.compile(r"(\d+) \((\d+\.\d)%\)")


def salt():
    try:
        with open(SALT_FILE, "r", encoding="utf-8") as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return 0


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


def phases(line):
    """label -> ms, from the 'host staging ...: name N (p%) ...' tail of a prefill timing line."""
    i = line.find("host staging")
    if i < 0:
        return {}
    seg = line[i:]
    out = {}
    for m in PHASE_RE.finditer(seg):
        head = seg[:m.start()]
        head = re.split(r"\d+ \(\d+\.\d%\) ", head)[-1]
        out[head.strip().rstrip(":")] = int(m.group(1))
    return out


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
    try:
        ask("warm up alpha bravo charlie delta echo foxtrot", 4, timeout=180)
        time.sleep(1.0)
        print("warm-up done", flush=True)
    except Exception as exc:                      # noqa: BLE001 - warm-up must never abort an arm
        print("warm-up ignored:", type(exc).__name__, flush=True)

    for ntok, reps in PRE:
        for i in range(reps):
            rng = random.Random(salt() + 90000 + ntok * 7 + i)
            prompt = " ".join(rng.choice(V) for _ in range(int(ntok * 0.82)))
            off = log_off()
            m, ln = [], ""
            for attempt in range(3):
                d, wall = ask(prompt, 2)
                time.sleep(0.3)
                new = read_new(off)
                hits = re.findall(r"(strata prefill timing: \d+ tokens, GPU timeline \d+ ms, wall \d+ ms.*)", new)
                if hits:
                    ln = hits[-1]
                    m = re.findall(r"strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms, wall (\d+) ms", ln)
                    break
                ct = (d.get("usage", {}).get("prompt_tokens_details") or {}).get("cached_tokens", 0)
                if ct and d.get("usage", {}).get("prompt_tokens") and ct >= d["usage"]["prompt_tokens"] - 1:
                    raise SystemExit("prompt was served from cache (cached=%d) - salt did not take" % ct)
                off = log_off()
                print("  retry %d for %d/%d" % (attempt + 1, ntok, i), flush=True)
                time.sleep(2.0)
            if not m:
                raise SystemExit("no prefill timing line for %d/%d after 3 tries" % (ntok, i))
            tk, gpu, wl = (int(x) for x in m[-1])
            rec = {"target": ntok, "tokens": tk, "gpu_ms": gpu, "wall_ms": wl,
                   "http_s": round(wall, 3), "phases": phases(ln)}
            res["prefill"].append(rec)
            print("prefill %5d -> tokens=%d gpu=%d wall=%d  attn=%s gu=%s down=%s deq=%s" % (
                ntok, tk, gpu, wl, rec["phases"].get("qsa attn"), rec["phases"].get("gemm gate/up"),
                rec["phases"].get("gemm down"), rec["phases"].get("dequant")), flush=True)

    for i in range(DEC):
        rng = random.Random(salt() + 70000 + i)
        prompt = " ".join(rng.choice(V) for _ in range(40))
        off = log_off()
        d, wall = ask(prompt, 128)
        time.sleep(0.25)
        new = read_new(off)
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
        print("decode %d -> %d tok in %d ms = %.1f tok/s" % (i, gen, ms, rate), flush=True)

    for ntok, _ in PRE:
        v = [r for r in res["prefill"] if r["target"] == ntok]
        if not v:
            continue
        per = [r["gpu_ms"] * 1000.0 / r["tokens"] for r in v]
        keys = set()
        for r in v:
            keys |= set(r["phases"])
        ph = {}
        for k in sorted(keys):
            xs = [r["phases"].get(k) for r in v if k in r["phases"]]
            if len(xs) == len(v):
                ph[k] = round(st.mean(xs), 1)
        wl = [r["wall_ms"] for r in v]
        res["prefill_summary_%d" % ntok] = {
            "n": len(v), "gpu_ms": round(st.mean([r["gpu_ms"] for r in v]), 1),
            "wall_ms": round(st.mean(wl), 1), "us_per_tok_gpu": round(st.mean(per), 1),
            "cv_pct_us_per_tok": round(100 * st.stdev(per) / st.mean(per), 1) if len(per) > 1 else 0.0,
            "phases_ms": ph}
    r = [x["tok_s"] for x in res["decode"]]
    res["decode_summary"] = {"n": len(r), "tok_s": round(st.mean(r), 2),
                             "cv_pct": round(100 * st.stdev(r) / st.mean(r), 1) if len(r) > 1 else 0.0}
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print("WROTE", out)


if __name__ == "__main__":
    main()
