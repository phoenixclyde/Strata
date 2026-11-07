import io

p = "ci/cfg_apply.py"
s = io.open(p, encoding="utf-8").read()

if "--lengths" not in s:
    s = s.replace('    ap.add_argument("--n", type=int, default=5)',
                  '    ap.add_argument("--n", type=int, default=5)\n'
                  '    ap.add_argument("--lengths", default="", help="extra prefill lengths to measure, e.g. 2000,8000,16000")',
                  1)

    # generic length probe next to ttft()
    s = s.replace("def stats(xs):", '''def prefill_at(n_tokens, n, warmup=1):
    """cold unique prompt of ~n_tokens; returns prompt tok/s samples (engine-side time is not parsed,
    wall time is used and the fixed cost is the same for both arms)."""
    rep = max(1, int(round(n_tokens / 10.2)))
    vals = []
    for i in range(n + warmup):
        prompt = "k%s " % secrets.token_hex(3) + "The quick brown fox jumps over the lazy dog. " * rep
        body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                           "max_tokens": 2, "temperature": 0.0}).encode()
        t0 = time.perf_counter()
        req = urllib.request.Request(URL + "/v1/chat/completions", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=900) as r:
            d = json.loads(r.read())
        pt = d.get("usage", {}).get("prompt_tokens", 0)
        dt = time.perf_counter() - t0
        if i >= warmup and dt:
            vals.append(pt / dt)
    return vals


def stats(xs):''', 1)

    # measure extra lengths in both the record-only path and the apply path
    s = s.replace('''        tt = stats(ttft(a.n))
        json.dump({"label": a.label''', '''        tt = stats(ttft(a.n))
        extra = {}
        for L in [int(x) for x in a.lengths.split(",") if x.strip()]:
            extra[L] = stats(prefill_at(L, max(3, a.n // 2)))
            print("   prefill@%d: %s" % (L, extra[L]))
        json.dump({"label": a.label''', 1)
    s = s.replace('''                   "decode": dec, "ttft": tt, "gate": "record-only"},''',
                  '''                   "decode": dec, "ttft": tt, "prefill": extra, "gate": "record-only"},''', 1)

    s = s.replace('''    dec = stats(decode(a.n))
    tt = stats(ttft(a.n))

    rec = {"label": a.label''', '''    dec = stats(decode(a.n))
    tt = stats(ttft(a.n))
    extra = {}
    for L in [int(x) for x in a.lengths.split(",") if x.strip()]:
        extra[L] = stats(prefill_at(L, max(3, a.n // 2)))
        print("   prefill@%d: %s" % (L, extra[L]))

    rec = {"label": a.label''', 1)
    s = s.replace('''           "decode": dec, "ttft": tt, "gate": "PASS"}''',
                  '''           "decode": dec, "ttft": tt, "prefill": extra, "gate": "PASS"}''', 1)

    # verdict: also flag a length-level regression beyond 2x CV
    s = s.replace('''            worse = dd < -band_d or dt2 > band_t''',
                  '''            worse = dd < -band_d or dt2 > band_t
            for L, cur in (extra or {}).items():
                base = (b.get("prefill") or {}).get(str(L)) or (b.get("prefill") or {}).get(L)
                if base and cur:
                    band = 2 * max(base["cv_pct"] or 0, cur["cv_pct"] or 0)
                    d = 100.0 * (cur["median"] - base["median"]) / base["median"]
                    print("   prefill@%d: %+.2f%% (band %.2f%%)" % (L, d, band))
                    if d < -band:
                        worse = True''', 1)

io.open(p, "w", encoding="utf-8").write(s)
print("patched --lengths")
