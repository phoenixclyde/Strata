# -*- coding: utf-8 -*-
"""W828o: TTFT with an explicit warm-up (so cold and warm engines compare like for like).
usage: python3 w828_ttft3.py <port> <lengths csv> <reps> <warmups>
"""
import json, sys, time, urllib.request, statistics as st, random

port = sys.argv[1] if len(sys.argv) > 1 else '8090'
lengths = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else '1200,2400,4800').split(',')]
reps = int(sys.argv[3]) if len(sys.argv) > 3 else 2
warmups = int(sys.argv[4]) if len(sys.argv) > 4 else 3

def post(body, timeout=1200):
    r = urllib.request.Request('http://127.0.0.1:%s/v1/chat/completions' % port,
                               data=json.dumps(body).encode(),
                               headers={'Content-Type': 'application/json'})
    t0 = time.time()
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        d = json.loads(resp.read())
    return time.time() - t0, d

with urllib.request.urlopen('http://127.0.0.1:%s/v1/models' % port, timeout=30) as resp:
    model = json.loads(resp.read())['data'][0]['id']

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
    words, target = [], int(n_tokens / 1.3)
    while len(words) < target:
        p = PARAS[rnd.randrange(len(PARAS))].split()
        rnd.shuffle(p)
        words += p
    return ("Unique document %d. Read it and reply with the single word OK.\n\n" % seed) + ' '.join(words[:target])

print('model:', model, '| warmups:', warmups)
for k in range(warmups):
    body = {'model': model, 'max_tokens': 1, 'temperature': 0,
            'messages': [{'role': 'user', 'content': make_prompt(900000 + k, 500)}]}
    dt, d = post(body)
    print('  warm-up %d  %.3f s  ptok=%s' % (k, dt, (d.get('usage') or {}).get('prompt_tokens')))

rows = []
print('%8s %4s %8s %10s' % ('target', 'idx', 'ptok', 'wall_s'))
for n in lengths:
    for k in range(reps):
        seed = 4200 * n + k + 11
        body = {'model': model, 'max_tokens': 1, 'temperature': 0,
                'messages': [{'role': 'user', 'content': make_prompt(seed, n)}]}
        dt, d = post(body)
        ptok = (d.get('usage') or {}).get('prompt_tokens', 0)
        rows.append((ptok, dt))
        print('%8d %4d %8d %10.3f' % (n, k, ptok, dt))

if len(rows) >= 3:
    xs = [r[0] for r in rows]; ys = [1000.0 * r[1] for r in rows]
    nn = len(xs); mx = sum(xs) / nn; my = sum(ys) / nn
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / max(sum((x - mx) ** 2 for x in xs), 1e-9)
    a = my - b * mx
    print()
    print('fit: TTFT_ms = %.0f + %.3f * tokens  (%.0f tok/s; min %.2f s, max %.2f s)'
          % (a, b, 1000.0 / b if b else 0, min(r[1] for r in rows), max(r[1] for r in rows)))
