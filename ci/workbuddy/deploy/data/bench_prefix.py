import json, sys, time, urllib.request

# 前缀复用探针：第 1 次冷 prefill，第 2 次在**同一 prompt 末尾追加一句**再发
# => 第 2 次的 TTFT 直接反映「前缀缓存 + 尾部 checkpoint」的效果。
BASE = 'http://127.0.0.1:8090/v1'
TAG = sys.argv[1]
# 可调长度：段数（PARA 约 45 token/段）。默认 400 ≈ 18,083 token（3 个 chunk）
PARAS = int(sys.argv[2]) if len(sys.argv) > 2 else 400
mdl = json.loads(urllib.request.urlopen(BASE + '/models', timeout=60).read().decode())['data'][0]['id']
PARA = ("The principal advantage of the configuration under test is that its working set fits "
        "entirely inside the memory hierarchy of the machine, so the steady state needs no disk "
        "access at all and the throughput is limited by compute rather than by storage. ")


def post(payload, timeout=3600):
    req = urllib.request.Request(BASE + '/chat/completions', data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    t0 = time.time(); tf = None; usage = None
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            ln = raw.decode('utf-8', 'replace').strip()
            if not ln.startswith('data:'):
                continue
            d = ln[5:].strip()
            if d == '[DONE]':
                break
            try:
                j = json.loads(d)
            except Exception:
                continue
            if j.get('usage'):
                usage = j['usage']
            for ch in (j.get('choices') or []):
                dc = ch.get('delta') or {}
                if dc.get('content') or dc.get('reasoning_content'):
                    if tf is None:
                        tf = time.time()
    te = time.time()
    u = usage or {}
    pt = u.get('prompt_tokens'); ct = u.get('completion_tokens')
    cached = ((u.get('prompt_tokens_details') or {}).get('cached_tokens'))
    return dict(pt=pt, ct=ct, ttft=(tf - t0) if tf else -1, cached=cached,
                pre=(pt / (tf - t0)) if pt and tf and t0 < tf else -1)


def body(salt, extra=''):
    # 段数由 argv[2] 决定：400 ≈ 18,083 token（3 chunk，存在边界）；150 ≈ 6,833 token（<1 chunk）
    t = ("Read the following text and answer with exactly one sentence.\n\n[%s]\n" % salt) \
        + (PARA * PARAS) + "\n\nQuestion: what is the principal advantage described?" + extra
    return {'model': mdl, 'messages': [{'role': 'user', 'content': t}],
            'max_tokens': 32, 'temperature': 0.0, 'stream': True,
            'stream_options': {'include_usage': True}}


print('===== PREFIX ARM %s =====' % TAG, flush=True)
post({'model': mdl, 'messages': [{'role': 'user', 'content': 'Reply with the single word OK.'}],
      'max_tokens': 16, 'temperature': 0.0, 'stream': True,
      'stream_options': {'include_usage': True}})

colds, warms, hc, hw = [], [], [], []
for i in range(2):
    salt = 'pfx-%s-%d' % (TAG, i)
    r1 = post(body(salt))
    colds.append(r1['ttft']); hc.append(r1['cached'] or 0)
    print('  pass%d COLD  pt=%s ttft=%.2fs pre=%.0f tok/s cached=%s' % (i + 1, r1['pt'], r1['ttft'], r1['pre'], r1['cached']), flush=True)
    r2 = post(body(salt, '\n\nNow add one more sentence about the same advantage.'))
    warms.append(r2['ttft']); hw.append(r2['cached'] or 0)
    print('  pass%d WARM  pt=%s ttft=%.3fs pre=%.0f tok/s cached=%s' % (i + 1, r2['pt'], r2['ttft'], r2['pre'], r2['cached']), flush=True)

print('SUMMARY %s cold_ttft median=%.2fs  warm_ttft median=%.3fs  warm_cached=%s' % (
    TAG, sorted(colds)[len(colds) // 2], sorted(warms)[len(warms) // 2], hw), flush=True)
