import io

p = "ci/cfg_apply.py"
s = io.open(p, encoding="utf-8").read()

if "secrets" not in s:
    s = s.replace("import statistics", "import secrets\nimport statistics", 1)

def block(start, end):
    return s[s.index(start):s.index(end)]

old_ttft = block("def ttft(", "def stats(")
new_ttft = '''def ttft(n, warmup=1):
    """2K-token prompt, a UNIQUE prefix per call: repeating the same prompt is a prefix
    hit (0.29 s measured), not a measurement."""
    vals = []
    for i in range(n + warmup):
        prompt = "ttft " + secrets.token_hex(4) + " " + "The quick brown fox jumps over the lazy dog. " * 200
        body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                           "max_tokens": 2, "temperature": 0.0}).encode()
        t0 = time.perf_counter()
        req = urllib.request.Request(URL + "/v1/chat/completions", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            r.read()
        dt = time.perf_counter() - t0
        if i >= warmup:
            vals.append(dt)
    return vals


def decode(n, tokens=64, warmup=1):
    vals = []
    for i in range(n + warmup):
        prompt = "decode " + secrets.token_hex(4) + " Count from 1 to 40, one number per line."
        body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                           "max_tokens": tokens, "temperature": 0.0}).encode()
        t0 = time.perf_counter()
        req = urllib.request.Request(URL + "/v1/chat/completions", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            d = json.loads(r.read())
        dt = time.perf_counter() - t0
        comp = d.get("usage", {}).get("completion_tokens", 0)
        if i >= warmup and dt:
            vals.append(comp / dt)
    return vals


'''
s = s.replace(old_ttft, new_ttft, 1)

# record-only: own probe instead of bench.py's JSON path
s = s.replace(
    '        bench = sh("python3 %s/bench.py --n %d --label %s-decode" % (HERE, a.n, a.label), timeout=1800)\n'
    '        rec_path = bench.stdout.strip().splitlines()[-1] if bench.stdout.strip() else ""\n'
    '        decode = json.load(open(rec_path))["metrics"]["tok_s"] if os.path.exists(rec_path) else None\n'
    '        tt = stats(ttft(a.n))',
    '        dec = stats(decode(a.n))\n        tt = stats(ttft(a.n))', 1)
s = s.replace('"decode": decode, "ttft": tt, "gate": "record-only"}',
              '"decode": dec, "ttft": tt, "gate": "record-only"}', 1)
s = s.replace('        print("   decode: %s" % decode)\n        print("   ttft  : %s" % tt)\n        print("   record:',
              '        print("   decode: %s" % dec)\n        print("   ttft  : %s" % tt)\n        print("   record:', 1)

# apply path
s = s.replace(
    '    bench = sh("python3 %s/bench.py --n %d --label %s-decode" % (HERE, a.n, a.label), timeout=1800)\n'
    '    rec_path = bench.stdout.strip().splitlines()[-1] if bench.stdout.strip() else ""\n'
    '    decode = None\n'
    '    if os.path.exists(rec_path):\n'
    '        decode = json.load(open(rec_path))["metrics"]["tok_s"]\n'
    '    tt = stats(ttft(a.n))',
    '    dec = stats(decode(a.n))\n    tt = stats(ttft(a.n))', 1)
s = s.replace('"decode": decode, "ttft": tt, "gate": "PASS"}',
              '"decode": dec, "ttft": tt, "gate": "PASS"}', 1)
s = s.replace('print("   decode: %s" % decode)', 'print("   decode: %s" % dec)', 1)
s = s.replace('if b.get("decode") and decode:', 'if b.get("decode") and dec:', 1)
s = s.replace('cv = max(b["decode"]["cv_pct"] or 0, decode["cv_pct"] or 0)',
              'cv = max(b["decode"]["cv_pct"] or 0, dec["cv_pct"] or 0)', 1)
s = s.replace('dd = 100.0 * (decode["median"] - b["decode"]["median"]) / b["decode"]["median"]',
              'dd = 100.0 * (dec["median"] - b["decode"]["median"]) / b["decode"]["median"]', 1)
s = s.replace('% (rec["ts"], a.label, decode and decode["median"], tt["median"], a.set + a.env))',
              '% (rec["ts"], a.label, dec["median"], tt["median"], a.set + a.env))', 1)

io.open(p, "w", encoding="utf-8").write(s)
print("patched probes; decode refs left:", s.count("decode and decode"))
