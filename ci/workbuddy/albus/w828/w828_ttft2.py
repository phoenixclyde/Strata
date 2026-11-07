# -*- coding: utf-8 -*-
"""W828k2: prefill curve with DISTINCT prompts (no prompt-cache hits), on the live server.
For each length, N different texts; report per-request wall time and the linear fit y = a + b*tokens.
usage: python3 w828_ttft2.py <port> <lengths csv> <n_distinct>
"""
import json, sys, time, urllib.request, statistics as st, random

port = sys.argv[1] if len(sys.argv) > 1 else '8090'
lengths = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else '1200,2400,4800').split(',')]
ndist = int(sys.argv[3]) if len(sys.argv) > 3 else 3

def post(path, body, timeout=900):
    r = urllib.request.Request('http://127.0.0.1:%s%s' % (port, path),
                               data=json.dumps(body).encode(),
                               headers={'Content-Type': 'application/json'})
    t0 = time.time()
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        d = json.loads(resp.read())
    return time.time() - t0, d

with urllib.request.urlopen('http://127.0.0.1:%s/v1/models' % port, timeout=30) as resp:
    model = json.loads(resp.read())['data'][0]['id']
print('model:', model)

PARAS = [
    ("In a quiet valley the engineers measured every stage of the pipeline, wrote the numbers down, and "
     "compared them with the previous run. They cared about the tails, not the means. "),
    ("The registry of tuning decisions grew by one line per experiment, and each line carried its own "
     "evidence, its own counter-evidence, and the date on which it was last re-checked. "),
    ("A cache keeps what is hot; a cache that guesses wrong costs more than it saves. That sentence was "
     "written on the whiteboard the morning the first measurement contradicted the model. "),
    ("When the window widened the reads did not amortise: the union of experts grew almost as fast as the "
     "row count, so every extra token arrived with its own private set of weights. "),
    ("Nothing here is a benchmark of the model's ability; it is a benchmark of the machine that carries "
     "it, and of the patience of the person waiting for the first token to appear. "),
]

def make_prompt(seed, n_tokens):
    rnd = random.Random(seed)
    words = []
    target = int(n_tokens / 1.3)
    while len(words) < target:
        p = PARAS[rnd.randrange(len(PARAS))].split()
        rnd.shuffle(p)
        words += p
    return ("Unique document %d. Read it and reply with the single word OK.\n\n" % seed) + ' '.join(words[:target])

rows = []
print('%8s %4s %8s %10s %8s' % ('target', 'idx', 'ptok', 'wall_s', 'ms/tok'))
for n in lengths:
    for k in range(ndist):
        seed = 1000 * n + k + 7
        body = {'model': model, 'max_tokens': 1, 'temperature': 0,
                'messages': [{'role': 'user', 'content': make_prompt(seed, n)}]}
        try:
            dt, d = post('/v1/chat/completions', body)
        except Exception as e:
            print('%8d %4d %8s %10s %8s  ERR %s' % (n, k, '-', '-', '-', str(e)[:50])); continue
        ptok = (d.get('usage') or {}).get('prompt_tokens', 0)
        rows.append((n, ptok, dt))
        print('%8d %4d %8d %10.3f %8.2f' % (n, k, ptok, dt, 1000.0 * dt / max(ptok, 1)))

print()
if len(rows) >= 3:
    xs = [r[1] for r in rows]; ys = [1000.0 * r[2] for r in rows]
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / max(sum((x - mx) ** 2 for x in xs), 1e-9)
    a = my - b * mx
    print('linear fit: TTFT_ms = %.0f + %.3f * tokens   (%.0f tok/s marginal)' % (a, b, 1000.0 / b if b else 0))
    print('at 500 / 1500 / 3000 / 8000 tok -> %.2f / %.2f / %.2f / %.2f s'
          % tuple((a + b * t) / 1000.0 for t in (500, 1500, 3000, 8000)))
