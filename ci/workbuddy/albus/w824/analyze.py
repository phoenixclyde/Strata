import json, os, re, statistics as st

D = '/home/albus/strata166/data'
arms = os.sys.argv[1:] or ['N0b', 'T1b', 'T2b']


def dec(path):
    try:
        d = json.load(open(path))
    except Exception:
        return None
    rows = d.get('results') or d.get('runs') or []
    vals = []
    for r in rows:
        v = r.get('decode_tps') or r.get('tok_per_s') or r.get('tps')
        if v:
            vals.append(float(v))
    return vals or None


def read(path):
    try:
        d = json.load(open(path))
    except Exception:
        return None
    return {r['prompt_tokens']: r['wall_s'] for r in d.get('results', []) if r.get('ok')}


def phases(arm):
    p = os.path.join(D, 'w824_%s.log' % arm)
    if not os.path.exists(p):
        return None
    out = {}
    ple = None
    for ln in open(p, encoding='utf-8', errors='replace'):
        if 'prefill timing:' in ln and 'GPU timeline' in ln:
            m = re.search(r'(\d+) tokens, GPU timeline (\d+) ms, wall (\d+) ms', ln)
            if not m:
                continue
            toks = int(m.group(1))
            seq = ln.split(':', 3)[-1]
            d = {}
            for mm in re.finditer(r'([a-z0-9 +/\-]+?) (\d+) \(([\d.]+)%\)', seq):
                d[mm.group(1).strip()] = (int(mm.group(2)), float(mm.group(3)))
            out[toks] = (int(m.group(2)), d)
        if 'host:' in ln and 'PLE' in ln:
            m = re.search(r'PLE (\d+) ms', ln)
            if m:
                ple = int(m.group(1))
    return out, ple


print('=== 读长（同语料，sha16 相同）===')
sizes = None
for a in arms:
    r = read(os.path.join(D, 'w824_%s.json' % a))
    if not r:
        print('%-4s 无数据' % a); continue
    sizes = sizes or sorted(r)
    print('%-4s ' % a + '  '.join('%d:%.2fs' % (k, r[k]) for k in sorted(r)))

print()
print('=== 解码（128 tok, T=0）===')
for a in arms:
    v = dec(os.path.join(D, 'w824_%s_dec.json' % a))
    if not v:
        print('%-4s 无数据' % a); continue
    print('%-4s n=%d  %s  median=%.1f' % (a, len(v), ' '.join('%.1f' % x for x in v), st.median(v)))

print()
print('=== 相位（GPU timeline 与 ple/attn 占比）===')
for a in arms:
    ph = phases(a)
    if not ph or not ph[0]:
        print('%-4s 无相位表' % a); continue
    tbl, hostple = ph
    for toks in sorted(tbl):
        total, d = tbl[toks]
        picks = [(k, v) for k, v in d.items() if k in ('ple', 'attn', 'gdn', 'hc read', 'gemmd', 'qsa proj', 'qsa select', 'moe', 'expert')]
        s = '  '.join('%s=%d(%.1f%%)' % (k, v[0], v[1]) for k, v in picks)
        print('%-4s %5d tok  total=%5d ms  hostPLE=%s  %s' % (a, toks, total, hostple, s))
