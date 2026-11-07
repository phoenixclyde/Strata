#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W828f: N concurrent greedy requests, per-stream decode tok/s from the server's own
per-request records (/metrics requests[]), plus the summed throughput.

usage: mt_gen2.py <port> <tag> <out.json> <corpus.json> [max_tokens] [n_streams] [n_rounds]
Each round fires n_streams requests at the same instant (threads), waits for all, then reads
/metrics and pairs the newest n_streams records with the streams by output length.
"""
import json
import sys
import threading
import time
import urllib.request

PORT = int(sys.argv[1])
TAG = sys.argv[2]
OUT = sys.argv[3]
CORPUS = sys.argv[4]
MAXT = int(sys.argv[5]) if len(sys.argv) > 5 else 512
NS = int(sys.argv[6]) if len(sys.argv) > 6 else 2
ROUNDS = int(sys.argv[7]) if len(sys.argv) > 7 else 3
B = 'http://127.0.0.1:%d' % PORT


def model_name():
    try:
        with urllib.request.urlopen(B + '/v1/models', timeout=10) as r:
            d = json.loads(r.read().decode()).get('data') or []
        if d and d[0].get('id'):
            return d[0]['id']
    except Exception:
        pass
    return 'default-big'


MODEL = model_name()
doc = json.load(open(CORPUS, encoding='utf-8'))
PROMPTS = doc['prompts']


def metrics():
    with urllib.request.urlopen(B + '/metrics', timeout=15) as r:
        return json.loads(r.read().decode())


def one(i, text, res, t0):
    body = {'model': MODEL, 'messages': [{'role': 'user', 'content': text}],
            'max_tokens': MAXT, 'temperature': 0.0, 'top_p': 1.0, 'reasoning_effort': 'none'}
    req = urllib.request.Request(B + '/v1/chat/completions', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            j = json.loads(r.read().decode())
        res[i] = {'ok': True, 'wall': round(time.time() - t0, 2),
                  'out': (j.get('usage') or {}).get('completion_tokens'),
                  'finish': j['choices'][0].get('finish_reason')}
    except Exception as e:
        res[i] = {'ok': False, 'err': repr(e)[:140]}


rows = []
for rnd in range(ROUNDS):
    res = {}
    texts = [PROMPTS[(rnd * NS + i) % len(PROMPTS)] for i in range(NS)]
    t0 = time.time()
    th = [threading.Thread(target=one, args=(i, texts[i], res, t0)) for i in range(NS)]
    for t in th:
        t.start()
    for t in th:
        t.join()
    time.sleep(0.4)
    recs = (metrics().get('requests') or [])[:NS]
    per = []
    for i in range(NS):
        r = res.get(i) or {}
        rec = recs[i] if i < len(recs) else {}
        dec, out = rec.get('decode_ms'), rec.get('output_tokens')
        tps = (1000.0 * out / dec) if (dec and out) else None
        per.append({'stream': i, 'ok': r.get('ok'), 'wall': r.get('wall'),
                    'out': out or r.get('out'), 'decode_ms': dec, 'tps': round(tps, 2) if tps else None})
    tot = sum(p['tps'] or 0.0 for p in per)
    rows.append({'round': rnd, 'streams': per, 'sum_tps': round(tot, 2)})
    print('  round%d  %s  SUM %.1f tok/s' % (
        rnd, '  '.join('s%d %s tok/s (%.0f ms)' % (p['stream'], p['tps'], p['decode_ms'] or 0) for p in per), tot))

ok = [r for r in rows if r['sum_tps'] > 0]
if ok:
    med = sorted(r['sum_tps'] for r in ok)
    mid = med[len(med) // 2] if len(med) % 2 else (med[len(med) // 2 - 1] + med[len(med) // 2]) / 2
    print('  MEDIAN SUM = %.2f tok/s over %d rounds (%d streams)' % (mid, len(ok), NS))
json.dump({'tag': TAG, 'streams': NS, 'max_tokens': MAXT, 'rows': rows}, open(OUT, 'w'), indent=1)
print('WROTE', OUT)
