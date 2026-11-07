# -*- coding: utf-8 -*-
"""W803 KL gate client: a scripted multi-turn conversation whose *shaping* turns are prefilled in
small (<1024 token) chunks -- the only regime where STRATA_PREFILL_CPU_SHARE acts -- and whose
*probe* turns are small enough to be read through the verify windows, so STRATA_LOGPOS scores them.

Why this shape (prefill.cpp:2882 `cpu_share_on() && !stream_all && !pipe_chunked`):
  * stream_all needs T >= 1024, so a >=1024-token chunk never uses the CPU share;
  * the logpos dump only exists for verify windows (generate.cpp:9543), and a window read is not a
    batched prefill, so the two can never happen on the same tokens.
=> the switch is injected by the shaping turns and *measured downstream* by the probe turns, which
   score the same token sequence in both arms on top of a K/V that was written differently.

Usage: mt_kl.py <corpus.json> <port> <tag> <out.json>
"""
import hashlib, json, sys, time, urllib.request

CORPUS, PORT, TAG, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]


def post(messages, max_tokens=1):
    body = {'model': 'default-big', 'messages': messages, 'max_tokens': max_tokens,
            'temperature': 0.0}
    req = urllib.request.Request('http://127.0.0.1:%d/v1/chat/completions' % PORT,
                                 data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=3600) as r:
            j = json.loads(r.read())
        u = j.get('usage', {}) or {}
        txt = (j['choices'][0]['message'].get('content') or '')
        return {'ok': True, 'prompt_tokens': u.get('prompt_tokens'),
                'completion_tokens': u.get('completion_tokens'),
                'wall_s': round(time.time() - t0, 2),
                'text_sha16': hashlib.sha256(txt.encode()).hexdigest()[:16]}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'wall_s': round(time.time() - t0, 2)}


doc = json.load(open(CORPUS, encoding='utf-8'))
turns = doc['turns']
res = []
hist = []
prev_pt = 0
for i, t in enumerate(turns):
    # the history is fully scripted: the assistant text is ours, never the engine's
    hist.append({'role': 'user', 'content': t['u']})
    rec = {'i': i, 'kind': t['kind'], 'phase': 'U', 'n_msgs': len(hist)}
    rec.update(post(hist))
    rec['fresh_est'] = None if rec.get('prompt_tokens') is None else rec['prompt_tokens'] - prev_pt
    if rec.get('prompt_tokens'):
        prev_pt = rec['prompt_tokens']
    res.append(rec)
    print('  t%-2d %-7s U prompt_tokens=%-6s fresh~%-5s wall=%.1fs %s'
          % (i, t['kind'], rec.get('prompt_tokens'), rec.get('fresh_est'), rec['wall_s'],
             rec.get('text_sha16') or rec.get('error') or ''), flush=True)
    if not rec.get('ok'):
        json.dump({'tag': TAG, 'port': PORT, 'results': res}, open(OUT, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print('CLIENT_ABORT ' + TAG, flush=True)
        sys.exit(1)
    # the assistant reply is scripted text, appended as a plain message: no generation is scored
    hist.append({'role': 'assistant', 'content': t['a']})
    if t.get('stop_after'):
        break
    time.sleep(0.5)

json.dump({'tag': TAG, 'port': PORT, 'results': res}, open(OUT, 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('CLIENT_DONE ' + TAG, flush=True)
