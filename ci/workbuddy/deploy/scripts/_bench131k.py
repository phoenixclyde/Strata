# -*- coding: utf-8 -*-
"""166：131072 上下文下的读数（含 30k / 100k 长预填）"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
cat > /home/albus/strata166/data/bench3.py <<'PYEOF'
import json, time, urllib.request

BASE = 'http://127.0.0.1:8090/v1'
mdl = json.loads(urllib.request.urlopen(BASE + '/models', timeout=60).read().decode())['data'][0]['id']
print('model =', mdl)

PARA = ("The principal advantage of the configuration under test is that its working set fits "
        "entirely inside the memory hierarchy of the machine, so the steady state needs no disk "
        "access at all and the throughput is limited by compute rather than by storage. ")

def build(nchars, q='what is the principal advantage described?', salt=''):
    body = (PARA * (nchars // len(PARA) + 1))[:nchars]
    return ("Read the following text and answer with exactly one sentence.\n\n" + salt + body
            + "\n\nQuestion: " + q)

def run(text, max_tokens, tag):
    payload = {'model': mdl, 'messages': [{'role': 'user', 'content': text}],
               'max_tokens': max_tokens, 'temperature': 0.0, 'stream': True,
               'stream_options': {'include_usage': True}}
    req = urllib.request.Request(BASE + '/chat/completions',
                                 data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    t0 = time.time(); tf = None; nd = 0; usage = None
    with urllib.request.urlopen(req, timeout=5400) as r:
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
                if dc.get('content') or dc.get('reasoning_content'):
                    if tf is None:
                        tf = time.time()
                    nd += 1
    te = time.time()
    pt = (usage or {}).get('prompt_tokens'); ct = (usage or {}).get('completion_tokens')
    ttft = (tf - t0) if tf else float('nan')
    print('--- %s ---' % tag)
    print('  prompt=%s completion=%s TTFT=%.2fs total=%.2fs prefill=%.1f tok/s decode=%.2f tok/s'
          % (pt, ct, ttft, te - t0, (pt / ttft) if pt and ttft else float('nan'),
             ((ct - 1) / (te - tf)) if ct and tf and te > tf else float('nan')))
    print()

print('=== R6 稳态解码（131k 配置）===')
run(build(1200), 256, 'R6 short-prompt 256 gen')
print('=== R7 约 30k token 冷预填 ===')
run(build(120000, salt='AAA '), 48, 'R7 ~30k prefill cold')
print('=== R8 同 prompt 复跑（前缀复用）===')
run(build(120000, salt='AAA '), 48, 'R8 ~30k prefill warm')
print('=== R9 约 100k token 冷预填（验证 131072 真能用）===')
run(build(400000, salt='BBB ', q='reply with the single word OK'), 16, 'R9 ~100k prefill cold')
PYEOF
echo "wrote rc=$?"
echo
docker exec strata166 python3 -u /data/bench3.py 2>&1
echo
echo "=== 引擎日志尾 22 ==="
docker exec strata166 bash -lc 'grep -E "prompt .* tokens =|expert cache hit rate|resident RAM:|expert tiers:|mtp|accept" /data/strata-ud-q4_k_xl.log | tail -22'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=7200)
with open(r'D:\strata166\logs\_bench131k.txt', 'w', encoding='utf-8') as f:
    f.write(r.stdout.decode('utf-8', 'replace'))
    if r.stderr.strip():
        f.write('\n--- STDERR ---\n' + r.stderr.decode('utf-8', 'replace')[:600])
print('done')
