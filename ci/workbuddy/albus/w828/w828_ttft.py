# -*- coding: utf-8 -*-
"""W828k: time-to-first-token curve on the LIVE production server (no restart).
Sends a prompt of ~N tokens with max_tokens=1 and times the whole request; repeats 3x per length.
usage: python3 w828_ttft.py <port> <lengths csv> <reps>
"""
import json, sys, time, urllib.request, statistics as st, os

port = sys.argv[1] if len(sys.argv) > 1 else '8090'
lengths = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else '500,1500,3000,8000').split(',')]
reps = int(sys.argv[3]) if len(sys.argv) > 3 else 3

def post(path, body, timeout=600):
    r = urllib.request.Request('http://127.0.0.1:%s%s' % (port, path),
                               data=json.dumps(body).encode(),
                               headers={'Content-Type': 'application/json'})
    t0 = time.time()
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        d = json.loads(resp.read())
    return time.time() - t0, d

# model name from the server, never hardcoded
with urllib.request.urlopen('http://127.0.0.1:%s/v1/models' % port, timeout=30) as resp:
    models = json.loads(resp.read())
model = models['data'][0]['id']
print('model:', model)

# a long, repetitive-but-natural body to build prompts from
para = ("The quick brown fox jumps over the lazy dog. In a quiet valley, engineers measured how long "
        "each stage of the pipeline took, wrote the numbers down, and compared them with the previous run. ")

def make_prompt(n_tokens):
    # ~1.3 tokens per English word; build by words
    words = max(20, int(n_tokens / 1.3))
    body = (para * (words // len(para.split()) + 2)).split()
    text = ' '.join(body[:words])
    return "Read the following text carefully and reply with the single word OK.\n\n" + text

print('%8s %8s %9s %9s' % ('target', 'req', 'wall_s', 'note'))
res = {}
for n in lengths:
    prompt = make_prompt(n)
    times = []
    for k in range(reps + 1):          # first one is a warm-up for this length
        body = {'model': model, 'max_tokens': 1, 'temperature': 0,
                'messages': [{'role': 'user', 'content': prompt}]}
        try:
            dt, d = post('/v1/chat/completions', body)
        except Exception as e:
            print('%8d %8s %9s %9s' % (n, 'ERR', '-', str(e)[:60])); break
        usage = (d.get('usage') or {})
        ptok = usage.get('prompt_tokens', 0)
        tag = 'warm' if k == 0 else 'r%d' % (k - 1)
        if k > 0:
            times.append(dt)
        print('%8d %8s %9.3f %9s' % (n, tag, dt, 'ptok=%d' % ptok))
    if times:
        res[n] = (st.median(times), ptok)
print()
print('%8s %8s %10s %12s %12s' % ('prompt', 'ptok', 'med_s', 'ms/token', 'vs 1k'))
base = None
for n, (med, ptok) in res.items():
    per = 1000.0 * med / max(ptok, 1)
    if base is None:
        base = per
    print('%8d %8d %10.3f %12.2f %12.2f' % (n, ptok, med, per, per / base))
