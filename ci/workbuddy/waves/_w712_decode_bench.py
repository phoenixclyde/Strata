# A2：0.1.40.4 解码基准（与历史同口径：预热 2 条 + 512 token x 3，temp 0 / top_k 1）
#   权威读数取 166 引擎日志里的 `N generated in M ms (X tok/s)` 行（含 MTP 接受数）
import json, sys, time, urllib.request, subprocess, base64

BASE = 'http://192.168.50.166:8090/v1'
MODEL = 'qwen3.8-flash-next-ud-iq4_xs'
LOG = '/home/albus/strata166/data/strata-ud-iq4_xs.log'

op = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def post(payload, timeout=1200):
    req = urllib.request.Request(BASE + '/chat/completions',
                                data=json.dumps(payload).encode(),
                                headers={'Content-Type': 'application/json'})
    t0 = time.time(); tf = None; usage = None
    with op.open(req, timeout=timeout) as r:
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
    ct = u.get('completion_tokens') or 0
    return dict(ct=ct, ttft=(tf - t0) if tf else -1,
                dec=(ct / (te - tf)) if (tf and te > tf and ct) else -1)


def ask(prompt, mt):
    return post({'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}],
                 'max_tokens': mt, 'temperature': 0.0, 'top_k': 1, 'stream': True,
                 'stream_options': {'include_usage': True}})


def tail_log(n=14):
    s = "tail -n %d %s" % (n, LOG)
    p = subprocess.run(['C:/Program Files/Git/usr/bin/ssh.exe', '-o', 'BatchMode=yes',
                        '-o', 'ConnectTimeout=8', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(s.encode()) + b'\n',
                       capture_output=True, timeout=60)
    return p.stdout.decode('utf-8', 'replace')


print('== 预热 2 条 ==', flush=True)
for i in range(2):
    r = ask('Say hello in one short sentence.', 64)
    print('  warm%d ct=%s ttft=%.2fs dec=%.2f' % (i + 1, r['ct'], r['ttft'], r['dec']), flush=True)

print('== 解码基准：512 token x 3（temp 0 / top_k 1）==', flush=True)
res = []
for i in range(3):
    t0 = time.time()
    r = ask('Write a detailed, continuous description of how a steam locomotive works, '
            'in long paragraphs, without stopping.', 512)
    res.append(r)
    print('  run%d ct=%s ttft=%.2fs dec=%.2f tok/s (wall %.1fs)' %
          (i + 1, r['ct'], r['ttft'], r['dec'], time.time() - t0), flush=True)

ds = sorted(x['dec'] for x in res if x['dec'] > 0)
print('DECODE_SUMMARY n=%d min=%.2f median=%.2f max=%.2f' %
      (len(ds), ds[0], ds[len(ds) // 2], ds[-1]), flush=True)

print('== 引擎日志（权威行）==', flush=True)
print(tail_log(16))
