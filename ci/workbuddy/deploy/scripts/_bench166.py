# -*- coding: utf-8 -*-
"""166：Strata 真机读数（TTFT / 解码 t/s / MTP 命中）"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
cat > /home/albus/strata166/data/bench.py <<'PYEOF'
import json, time, urllib.request

BASE = 'http://127.0.0.1:8090/v1'
LOG  = '/data/strata-ud-q4_k_xl.log'

def get(p):
    with urllib.request.urlopen(BASE + p, timeout=60) as r:
        return r.read().decode()

print('=== /v1/models ===')
mdl = ''
try:
    j = json.loads(get('/models'))
    mdl = j['data'][0]['id']
    print(' model id =', mdl)
    print(' raw:', json.dumps(j, ensure_ascii=False)[:400])
except Exception as e:
    print(' ERR', e)
    raise SystemExit(1)

PARA = ("The principal advantage of the configuration under test is that its working set fits "
        "entirely inside the memory hierarchy of the machine, so the steady state needs no disk "
        "access at all and the throughput is limited by compute rather than by storage. ")

def build(nchars):
    body = (PARA * (nchars // len(PARA) + 1))[:nchars]
    return ("Read the following text and answer with exactly one sentence.\n\n"
            + body + "\n\nQuestion: what is the principal advantage described?")

def logsize():
    try:
        import os; return os.path.getsize(LOG)
    except Exception: return 0

def run(text, max_tokens, tag):
    payload = {'model': mdl, 'messages': [{'role': 'user', 'content': text}],
               'max_tokens': max_tokens, 'temperature': 0.0, 'stream': True,
               'stream_options': {'include_usage': True}}
    req = urllib.request.Request(BASE + '/chat/completions',
                                 data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    before = logsize()
    t0 = time.time(); t_first = None; ndelta = 0; usage = None; buf = ''
    with urllib.request.urlopen(req, timeout=1800) as r:
        for raw in r:
            line = raw.decode('utf-8', 'replace').strip()
            if not line.startswith('data:'):
                continue
            d = line[5:].strip()
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
                c = dc.get('content') or dc.get('reasoning_content') or ''
                if c:
                    if t_first is None:
                        t_first = time.time()
                    ndelta += 1
                    buf += c
    t_end = time.time()
    pt = (usage or {}).get('prompt_tokens')
    ct = (usage or {}).get('completion_tokens')
    ttft = (t_first - t0) if t_first else float('nan')
    dec = ((ct - 1) / (t_end - t_first)) if (ct and t_first and t_end > t_first) else float('nan')
    print('--- %s ---' % tag)
    print('  prompt_tokens=%s  completion_tokens=%s  deltas=%s' % (pt, ct, ndelta))
    print('  TTFT=%.2fs  total=%.2fs  prefill=%.1f tok/s  decode=%.2f tok/s'
          % (ttft, t_end - t0, (pt / ttft) if pt and ttft else float('nan'), dec))
    print('  head: %r' % buf[:150])
    print('  usage: %s' % json.dumps(usage))
    # 引擎日志新增行里的 mtp / accept 信息
    try:
        with open(LOG, 'r', encoding='utf-8', errors='replace') as f:
            f.seek(before)
            new = f.read()
        keys = [l for l in new.splitlines() if any(k in l.lower() for k in ('mtp', 'accept', 'spec', 'rate'))]
        for l in keys[-8:]:
            print('  [log]', l.strip()[:170])
    except Exception as e:
        print('  [log] ERR', e)
    print()

text_s = build(1200)
text_l = build(12000)
print('=== 跑 3 轮 ===')
run(text_s, 128, 'R1 short-prompt')
run(text_l, 256, 'R2 long-prompt (~3k tok)')
run(text_l, 256, 'R3 long-prompt repeat')
PYEOF
echo "wrote bench.py rc=$?"
echo
docker exec strata166 python3 /data/bench.py 2>&1
echo
echo "=== 引擎日志尾 40 ==="
docker exec strata166 bash -lc 'tail -40 /data/strata-ud-q4_k_xl.log'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=1800)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('--- STDERR ---')
    print(r.stderr.decode('utf-8', 'replace')[:800])
