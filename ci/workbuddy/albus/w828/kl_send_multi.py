#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W828g: N prompts of the same length from different parts of the pool, so each one's verify
window scores a few positions and the dumps accumulate. Both arms send them in the same order,
so the scored positions line up.
usage: kl_send_multi.py <port> <prompts.json> <tag> [max_tokens=1]"""
import json
import sys
import time
import urllib.request

PORT = int(sys.argv[1])
CORPUS = sys.argv[2]
TAG = sys.argv[3] if len(sys.argv) > 3 else 'x'
MAXT = int(sys.argv[4]) if len(sys.argv) > 4 else 1
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


M = model_name()
prompts = json.load(open(CORPUS, encoding='utf-8'))['prompts']
for i, text in enumerate(prompts):
    body = {'model': M, 'messages': [{'role': 'user', 'content': text}],
            'max_tokens': MAXT, 'temperature': 0.0, 'top_p': 1.0, 'reasoning_effort': 'none'}
    req = urllib.request.Request(B + '/v1/chat/completions', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            j = json.loads(r.read().decode())
        u = j.get('usage') or {}
        print('  p%-2d tokens=%s wall=%.1fs' % (i, u.get('prompt_tokens'), time.time() - t0), flush=True)
    except Exception as e:
        print('  p%-2d FAILED %r' % (i, e), flush=True)
