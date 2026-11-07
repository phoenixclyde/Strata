# -*- coding: utf-8 -*-
"""166 收尾测量：① 干净解码基准（预热+512token×3）② SSD 随机读刻画（验基线漂移假设）"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
cat > /home/albus/strata166/data/final_bench.py <<'PYEOF'
import json, os, time, urllib.request, random

BASE = 'http://127.0.0.1:8090/v1'
LOG  = '/data/strata-ud-q4_k_xl.log'
mdl  = json.loads(urllib.request.urlopen(BASE + '/models', timeout=60).read().decode())['data'][0]['id']
print('model =', mdl, flush=True)

def chat(text, max_tokens, temp=0.0):
    payload = {'model': mdl, 'messages': [{'role': 'user', 'content': text}],
               'max_tokens': max_tokens, 'temperature': temp, 'top_k': 1, 'top_p': 1,
               'stream': True, 'stream_options': {'include_usage': True}}
    req = urllib.request.Request(BASE + '/chat/completions', data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    t0 = time.time(); tf = None; usage = None
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
    te = time.time()
    pt = (usage or {}).get('prompt_tokens'); ct = (usage or {}).get('completion_tokens')
    return dict(pt=pt, ct=ct, ttft=(tf - t0) if tf else -1,
                dec=((ct - 1) / (te - tf)) if ct and tf and te > tf else -1,
                pre=(pt / (tf - t0)) if pt and tf and tf > t0 else -1)

def tail(n=6):
    try:
        with open(LOG, 'rb') as f:
            f.seek(0, 2); sz = f.tell(); f.seek(max(0, sz - 200000))
            return f.read().decode('utf-8', 'replace').splitlines()[-n:]
    except Exception:
        return []

# ---------- ① 干净解码基准 ----------
print('=== 预热 2 条 ===', flush=True)
for i in range(2):
    r = chat('Reply with the single word OK.', 16)
    print('  warm%d dec=%.2f' % (i + 1, r['dec']), flush=True)

print('=== 解码基准：512 token × 3（temp 0 / top_k 1）===', flush=True)
res = []
for i in range(3):
    r = chat('Write a detailed technical explanation of how a solid-state drive '
             'handles garbage collection, in at least 400 words.', 512)
    res.append(r)
    print('  run%d prompt=%s completion=%s TTFT=%.2fs prefill=%.1f t/s decode=%.2f t/s'
          % (i + 1, r['pt'], r['ct'], r['ttft'], r['pre'], r['dec']), flush=True)
    for ln in tail(8):
        if 'generated in' in ln and 'decode expert cache' not in ln:
            print('    [log]', ln.strip()[:160], flush=True)
vals = [x['dec'] for x in res if x['dec'] > 0]
print('DECODE_SUMMARY n=%d min=%.2f median=%.2f max=%.2f'
      % (len(vals), min(vals), sorted(vals)[len(vals)//2], max(vals)), flush=True)

# ---------- ② SSD 随机读刻画 ----------
import fcntl, mmap, struct
def direct_rand_read(path, n=1500, bs=4096, off_limit=None):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECT)
    try:
        st = os.fstat(fd); size = st.st_size
        lim = min(size - bs, off_limit or size)
        align = bs
        offs = [random.randrange(0, max(1, lim // align)) * align for _ in range(n)]
        buf = mmap.mmap(-1, bs)
        lat = []
        for off in offs:
            t = time.perf_counter()
            os.preadv(fd, [buf], off)
            lat.append((time.perf_counter() - t) * 1e6)
        lat.sort()
        return dict(n=n, p50=lat[len(lat)//2], p95=lat[int(len(lat)*0.95)],
                    mean=sum(lat)/len(lat), iops=1e6/(sum(lat)/len(lat)))
    finally:
        os.close(fd)

P1 = '/weights/Qwen3.8-Flash-Next-UD-Q4_K_XL-00002-of-00004.gguf'   # 含 PLE 表
P2 = '/weights/Qwen3.8-Flash-Next-UD-Q4_K_XL-00003-of-00004.gguf'
print('=== SSD 随机 4K 读延迟（O_DIRECT）===', flush=True)
for p in (P1, P2):
    try:
        d = direct_rand_read(p, 1200)
        print('  %s  n=%d p50=%.0fus p95=%.0fus mean=%.0fus -> %.0f IOPS'
              % (os.path.basename(p)[-28:], d['n'], d['p50'], d['p95'], d['mean'], d['iops']), flush=True)
    except Exception as e:
        print('  %s ERR %s' % (os.path.basename(p), str(e)[:120]), flush=True)

print('=== SSD 顺序读（O_DIRECT 8MB × 3 次）===', flush=True)
try:
    fd = os.open(P1, os.O_RDONLY | os.O_DIRECT)
    bs = 8 << 20
    buf = mmap.mmap(-1, bs)
    rates = []
    for i in range(3):
        off = random.randrange(0, (os.fstat(fd).st_size - bs) // 4096) * 4096
        t = time.perf_counter(); os.preadv(fd, [buf], off); dt = time.perf_counter() - t
        rates.append(bs / dt / 1e6)
    os.close(fd)
    print('  %.0f / %.0f / %.0f MB/s' % tuple(rates), flush=True)
except Exception as e:
    print('  ERR', str(e)[:140], flush=True)

print('=== 内存/负载 ===', flush=True)
print(open('/proc/loadavg').read().strip())
PYEOF
echo "wrote rc=$?"
echo
docker exec strata166 python3 -u /data/final_bench.py 2>&1
echo
echo "=== 引擎日志：本次全部读数 ==="
docker exec strata166 bash -lc 'egrep "prompt [0-9]+ tokens|decode expert cache hit rate|resident RAM:" /data/strata-ud-q4_k_xl.log | tail -12'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=3600)
with open(r'D:\strata166\logs\_final_bench.txt', 'w', encoding='utf-8') as f:
    f.write(r.stdout.decode('utf-8', 'replace'))
    if r.stderr.strip():
        f.write('\n--- STDERR ---\n' + r.stderr.decode('utf-8', 'replace')[:600])
print('done -> D:\\strata166\\logs\\_final_bench.txt')
