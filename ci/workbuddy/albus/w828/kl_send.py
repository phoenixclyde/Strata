#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W828g: one long prompt + a long greedy continuation, so STRATA_LOGPOS scores hundreds of
positions (it only scores tokens the verify windows read: prompt tail + every decode window).
usage: kl_send.py <port> <prompt.json> [tag] [max_tokens]"""
import json
import sys
import time
import urllib.request

PORT = int(sys.argv[1])
CORPUS = sys.argv[2]
TAG = sys.argv[3] if len(sys.argv) > 3 else 'x'
MAXT = int(sys.argv[4]) if len(sys.argv) > 4 else 900
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


text = json.load(open(CORPUS, encoding='utf-8'))['prompt']
body = {'model': model_name(), 'messages': [{'role': 'user', 'content': text}],
        'max_tokens': MAXT, 'temperature': 0.0, 'top_p': 1.0, 'reasoning_effort': 'none'}
req = urllib.request.Request(B + '/v1/chat/completions', data=json.dumps(body).encode(),
                             headers={'Content-Type': 'application/json'})
t0 = time.time()
with urllib.request.urlopen(req, timeout=3600) as r:
    j = json.loads(r.read().decode())
u = j.get('usage') or {}
print('  prompt_tokens=%s completion=%s wall=%.1fs finish=%s'
      % (u.get('prompt_tokens'), u.get('completion_tokens'), time.time() - t0,
         j['choices'][0].get('finish_reason')))
