import json, os, re, statistics as st

D = '/home/albus/strata166/data'
arms = os.sys.argv[1:] or ['N1', 'A1', 'V1']


def read(path):
    try:
        d = json.load(open(path))
    except Exception:
        return None
    return {r['prompt_tokens']: r['wall_s'] for r in d.get('results', []) if r.get('ok')}


def dec(path):
    try:
        d = json.load(open(path))
    except Exception:
        return None
    v = []
    for r in (d.get('results') or []):
        x = r.get('decode_tps') or r.get('tok_per_s')
        if x:
            v.append(float(x))
    return v or None


def prefill_phases(arm):
    p = os.path.join(D, 'w824_%s.log' % arm)
    if not os.path.exists(p):
        return {}
    out = {}
    for ln in open(p, encoding='utf-8', errors='replace'):
        if 'prefill timing:' in ln and 'GPU timeline' in ln:
            m = re.search(r'(\d+) tokens, GPU timeline (\d+) ms', ln)
            if not m:
                continue
            d = {}
            for mm in re.finditer(r'([a-z0-9 +/\-]+?) (\d+) \(([\d.]+)%\)', ln.split(':', 3)[-1]):
                d[mm.group(1).strip()] = (int(mm.group(2)), float(mm.group(3)))
            out[int(m.group(1))] = (int(m.group(2)), d)
    return out


def decode_timing(arm):
    """取每个请求的 decode timing 行，返回 [(ms/window, verify, draft, tok/win)]"""
    p = os.path.join(D, 'w824_%s.log' % arm)
    if not os.path.exists(p):
        return []
    rows = []
    for ln in open(p, encoding='utf-8', errors='replace'):
        if not ln.startswith('strata decode timing:'):
            continue
        m = re.search(r'avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window = .*?verify ([\d.]+)', ln)
        md = re.search(r'\+ draft ([\d.]+)', ln)
        if m:
            rows.append((float(m.group(3)), float(m.group(4)), float(md.group(1)) if md else 0.0, float(m.group(2))))
    return rows


print('=== prefill（wall）===')
for a in arms:
    r = read(os.path.join(D, 'w824_%s.json' % a))
    print('%-3s %s' % (a, '  '.join('%d:%.2fs' % (k, r[k]) for k in sorted(r)) if r else '无'))

print()
print('=== prefill 相位：attn / gate+up / down（GPU timeline ms）===')
for a in arms:
    ph = prefill_phases(a)
    for toks in sorted(ph)[-2:]:
        total, d = ph[toks]
        def g(k):
            return d.get(k, (0, 0))[0]
        print('%-3s %5d tok total=%5d  attn=%4d  gate/up=%4d  down=%4d  gdn=%4d  hc=%4d  ple=%3d'
              % (a, toks, total, g('attn'), g('gate/up'), g('gemm down'), g('gdn'), g('hc read'), g('ple')))

print()
print('=== 解码：tok/s 中位 与 decode timing 的 ms/window ===')
for a in arms:
    v = dec(os.path.join(D, 'w824_%s_dec.json' % a))
    t = decode_timing(a)
    s1 = 'median=%.1f (n=%d)' % (st.median(v), len(v)) if v else '无 tok/s'
    if t:
        ms = st.median([x[0] for x in t])
        ve = st.median([x[1] for x in t])
        dr = st.median([x[2] for x in t])
        tw = st.median([x[3] for x in t])
        s2 = 'ms/win=%.1f (verify %.1f + draft %.1f), %.2f tok/win, n=%d' % (ms, ve, dr, tw, len(t))
    else:
        s2 = '无 decode timing'
    print('%-3s %-28s %s' % (a, s1, s2))
