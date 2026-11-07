# -*- coding: utf-8 -*-
"""0.1.39 vs 0.1.40.1 单变量对拍（三臂：39 → 401 → 39 复测）

设计（按 2026-10-06 审计结论）：
  · 单点比较不可靠 —— 本机存在约 12% 的未归因波动
  · 所以：每臂先**预热一次丢弃**，再**重复 3 次取中位与极差**
  · 末臂回到 0.1.39 作同条件对照，用来判定"臂间差异"是否只是漂移
配置完全一致（同一份 /data/strata-ud-q4_k_xl.json），**唯一变量 = 引擎版本**。
"""
import base64, os, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
CONF = '/data/strata-ud-q4_k_xl.json'
WS = '/src'


def ssh(sc, t=3600):
    b = base64.b64encode(sc.encode('utf-8')).decode('ascii')
    r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                        '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                       input=b.encode('ascii'), capture_output=True, timeout=t)
    return r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


BENCH = r'''cat > /home/albus/strata166/data/bench_ver.py <<'PYEOF'
import json, sys, time, urllib.request
BASE = 'http://127.0.0.1:8090/v1'
TAG = sys.argv[1]
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
            try: j = json.loads(d)
            except Exception: continue
            if j.get('usage'): usage = j['usage']
            for ch in (j.get('choices') or []):
                dc = ch.get('delta') or {}
                if dc.get('content') or dc.get('reasoning_content'):
                    if tf is None: tf = time.time()
    te = time.time()
    pt = (usage or {}).get('prompt_tokens'); ct = (usage or {}).get('completion_tokens')
    return dict(pt=pt, ct=ct, ttft=(tf - t0) if tf else -1,
                pre=(pt / (tf - t0)) if pt and tf and tf > t0 else -1,
                dec=((ct - 1) / (te - tf)) if ct and tf and te > tf else -1)

def prefill_probe(salt):
    body = (PARA * 400)[:]
    text = ("Read the following text and answer with exactly one sentence.\n\n[%s]\n" % salt) + body + \
           "\n\nQuestion: what is the principal advantage described?"
    return post({'model': mdl, 'messages': [{'role': 'user', 'content': text}],
                 'max_tokens': 48, 'temperature': 0.0, 'stream': True,
                 'stream_options': {'include_usage': True}})

def decode_probe():
    return post({'model': mdl, 'messages': [{'role': 'user', 'content':
                 'Write a detailed technical explanation of how a solid-state drive handles '
                 'garbage collection, in at least 400 words.'}],
                 'max_tokens': 512, 'temperature': 0.0, 'top_k': 1, 'top_p': 1, 'stream': True,
                 'stream_options': {'include_usage': True}})

print('===== ARM %s =====' % TAG, flush=True)
print('[warmup] ...', flush=True)
w = post({'model': mdl, 'messages': [{'role': 'user', 'content': 'Reply with the single word OK.'}],
          'max_tokens': 16, 'temperature': 0.0, 'stream': True,
          'stream_options': {'include_usage': True}})
print('  warmup decode=%.2f t/s' % w['dec'], flush=True)

pres, decs = [], []
for i in range(3):
    r = prefill_probe('arm-%s-run%d' % (TAG, i))
    pres.append(r['pre'])
    print('  prefill#%d prompt=%s  %.1f tok/s (%.2f ms/token)' % (i + 1, r['pt'], r['pre'],
          1000.0 / r['pre'] if r['pre'] > 0 else -1), flush=True)
for i in range(3):
    r = decode_probe()
    decs.append(r['dec'])
    print('  decode#%d completion=%s  %.2f tok/s' % (i + 1, r['ct'], r['dec']), flush=True)

def stat(v):
    s = sorted(v)
    return 'median=%.1f min=%.1f max=%.1f spread=%.1f%%' % (s[1], s[0], s[2], (s[2]-s[0])/s[1]*100 if s[1] else -1)
print('SUMMARY %s prefill %s' % (TAG, stat(pres)), flush=True)
print('SUMMARY %s decode  %s' % (TAG, stat(decs)), flush=True)
PYEOF
echo "bench written rc=$?"'''

print('[1] 写入对拍脚本'); o, e = ssh(BENCH, 300); print(o, e[:200])

ARMS = [
    ('0.1.39', 'strata166', 'strata-gfx906:0.1.39'),
    ('0.1.40.1', 'strata166-401', 'strata-gfx906:0.1.40.1'),
    ('0.1.39-again', 'strata166', 'strata-gfx906:0.1.39'),
]

for label, cname, img in ARMS:
    print()
    print('#' * 70)
    print('# ARM %s  容器=%s 镜像=%s' % (label, cname, img))
    print('#' * 70, flush=True)

    # 停掉所有占 8090 的实例（自免正则，别杀到自己）
    o, e = ssh(r'''
set +e
for n in strata166 strata166-401; do
  if docker ps -a --format '{{.Names}}' | grep -qx "$n"; then docker stop -t 20 "$n" >/dev/null 2>&1; echo "stopped $n"; fi
done
sleep 3
docker ps --format '{{.Names}}|{{.Status}}' | grep -i strata || echo "(无 strata 容器在跑)"
''', 300)
    print(o.strip(), flush=True)

    if cname == 'strata166-401':
        o, e = ssh(r'''
set -e
if ! docker ps -a --format '{{.Names}}' | grep -qx strata166-401; then
  docker run -d --name strata166-401 \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    --ipc=host --ulimit memlock=-1 \
    -v /home/albus/strata166/weights:/weights:ro \
    -v /home/albus/strata166/data:/data \
    -p 8090:8090 \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
    --restart no \
    strata-gfx906:0.1.40.1 sleep infinity
else
  docker start strata166-401
fi
sleep 2
docker ps --format '{{.Names}}|{{.Status}}' | grep strata166-401
''', 600)
        print('  [container]', o.strip(), e[:200], flush=True)

    o, e = ssh('docker start %s >/dev/null 2>&1; sleep 2; docker exec -d %s bash -lc \'cd %s && setsid nohup python3 serve/server.py --engine strata --config %s --port 8090 > /data/serve-run.log 2>&1 < /dev/null\'; echo started'
               % (cname, cname, WS, CONF), 300)
    print('  [start]', o.strip(), flush=True)

    ready = False
    for i in range(30):
        time.sleep(20)
        # 就绪判据用 HTTP 探针（曾在日志里被 "ready" 字样误触，故不再用 grep 判活）
        o, _ = ssh('docker exec %s bash -lc \'curl -s -o /dev/null -w "%%{http_code}" '
                   'http://127.0.0.1:8090/v1/models; echo; tail -1 /data/serve-run.log\'' % cname, 120)
        code = (o.strip().splitlines() or [''])[0].strip()
        tail = (o.strip().splitlines() or ['', ''])[-1][:100]
        print('  [%3ds] http=%s  %s' % ((i + 1) * 20, code, tail), flush=True)
        if code == '200':
            print('  [ready @ %ds]' % ((i + 1) * 20), flush=True)
            ready = True
            break
    if not ready:
        o, _ = ssh('docker exec %s bash -lc \'tail -20 /data/serve-run.log; echo ---; tail -8 /data/strata-ud-q4_k_xl.log\'' % cname, 180)
        print('  [!! 未就绪]'); print(o[-1500:], flush=True)
        continue

    o, _ = ssh('docker exec %s python3 -u /data/bench_ver.py %s 2>&1' % (cname, label), 3600)
    print(o, flush=True)

print()
print('=== 引擎日志读数核对（各臂最后 3 条 prompt 计时行）===')
o, _ = ssh(r'''grep -E "prompt [0-9]+ tokens = 0 reused" /data/strata-ud-q4_k_xl.log | tail -12''', 180)
print(o, flush=True)
