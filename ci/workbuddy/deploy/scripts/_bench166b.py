# -*- coding: utf-8 -*-
"""166：稳态解码 + 长预填 + VRAM/旋钮"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
cat > /home/albus/strata166/data/bench2.py <<'PYEOF'
import json, time, urllib.request

BASE = 'http://127.0.0.1:8090/v1'
LOG  = '/data/strata-ud-q4_k_xl.log'
mdl  = json.loads(urllib.request.urlopen(BASE + '/models', timeout=60).read().decode())['data'][0]['id']

PARA = ("The principal advantage of the configuration under test is that its working set fits "
        "entirely inside the memory hierarchy of the machine, so the steady state needs no disk "
        "access at all and the throughput is limited by compute rather than by storage. ")

def build(nchars, q="what is the principal advantage described?"):
    body = (PARA * (nchars // len(PARA) + 1))[:nchars]
    return ("Read the following text and answer with exactly one sentence.\n\n" + body + "\n\nQuestion: " + q)

def run(text, max_tokens, tag, temp=0.0):
    payload = {'model': mdl, 'messages': [{'role': 'user', 'content': text}],
               'max_tokens': max_tokens, 'temperature': temp, 'stream': True,
               'stream_options': {'include_usage': True}}
    req = urllib.request.Request(BASE + '/chat/completions',
                                 data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    t0 = time.time(); tf = None; nd = 0; usage = None
    with urllib.request.urlopen(req, timeout=3600) as r:
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
    print('  prompt=%s  completion=%s  TTFT=%.2fs  total=%.2fs  prefill=%.1f tok/s  decode=%.2f tok/s'
          % (pt, ct, ttft, te - t0, (pt / ttft) if pt and ttft else float('nan'),
             ((ct - 1) / (te - tf)) if ct and tf and te > tf else float('nan')))
    print()

print('=== R4 稳态解码 512 tok（热）===')
run(build(1200), 512, 'R4 512-token generation')
print('=== R5 长预填 ~6000 tok（同前缀已热）===')
run(build(24000, 'summarize in one sentence'), 64, 'R5 long prefill warm-prefix')
PYEOF
echo "wrote rc=$?"
echo
docker exec strata166 python3 /data/bench2.py 2>&1
echo
echo "=== 引擎日志尾 14 ==="
docker exec strata166 bash -lc 'grep -E "prompt .* tokens =|expert cache hit rate|resident RAM:|expert tiers:" /data/strata-ud-q4_k_xl.log | tail -14'
echo
echo "=== VRAM / GPU ==="
docker exec strata166 bash -lc 'rocm-smi --showmeminfo vram 2>/dev/null | head -12; echo; rocm-smi --showuse --showtemp 2>/dev/null | head -10'
echo
echo "=== 引擎旋钮（kv / prompt / pool / resident）==="
docker exec strata166 bash -lc '/src/build-906/strata --help 2>&1 | grep -iE "kv|prompt|chunk|resident|pool|spec|mtp|context" | head -40'
echo
echo "=== 内存 ==="
docker exec strata166 bash -lc 'free -g | head -2'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=1800)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('--- STDERR ---')
    print(r.stderr.decode('utf-8', 'replace')[:800])
