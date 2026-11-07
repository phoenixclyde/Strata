# -*- coding: utf-8 -*-
"""把上下文优化落到 serve：--max-context 262144 --kv k8v4
   → 写配置 → 重启 → 等就绪 → 用 bench_ver.py 实测（预填 18k × 3 + 解码 512 × 3）
"""
import base64, json, os, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
C = 'strata166-401'
CONF = '/data/strata-ud-iq4_xs.json'
PACK = '/data/packs/ud-iq4_xs'
GGUF1 = '/weights/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf'
LOG = '/data/strata-ud-iq4_xs.log'
NAME = 'qwen3.8-flash-next-ud-iq4_xs'

NEW_CTX = '262144'
NEW_KV = 'k8v4'


def ssh(sc, t=3600):
    b = base64.b64encode(sc.encode('utf-8')).decode('ascii')
    r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                        '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                       input=b.encode('ascii'), capture_output=True, timeout=t)
    return r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


def ensure_running():
    ssh("docker start %s 2>&1; echo rc=$?" % C, 300)
    for i in range(30):
        o, _ = ssh("docker inspect -f '{{.State.Running}}' %s 2>&1" % C, 120)
        if o.strip().splitlines()[-1].strip() == 'true':
            o2, _ = ssh("docker exec %s bash -lc 'python3 -c \"print(1)\"'" % C, 120)
            if '1' in o2:
                print('    容器就绪', flush=True)
                return True
        time.sleep(2)
    raise SystemExit('容器未就绪')


print('[1] 备份旧配置并写新配置（ctx %s / kv %s）' % (NEW_CTX, NEW_KV), flush=True)
ssh("docker exec %s bash -lc 'cp -n %s %s.bak-131k-int8 2>/dev/null; ls -l %s*'"
    % (C, CONF, CONF, CONF), 300)
cfg = {
    "exe": "/src/build-906/strata",
    "args": [
        "--pack", PACK,
        "--native", GGUF1,
        "--resident-budget-gib", "76",
        "--expert-profile", "/src/data/expert-profile.bin",
        "--expert-cache", "auto",
        "--spec", "4",
        "--spec-min-p", "0.5",
        "--mtp", "/data/mtp/rt",
        "--max-context", NEW_CTX,
        "--kv", NEW_KV,
        "--prefill", "auto",
    ],
    "cwd": "/src",
    "tokenizer": PACK + "/tokenizer",
    "model_name": NAME,
    "log": LOG,
    "host": "0.0.0.0",
    "port": 8090,
}
body = json.dumps(cfg, indent=1)
b64 = base64.b64encode(body.encode()).decode('ascii')
o, e = ssh("echo %s | base64 -d | docker exec -i %s bash -lc 'cat > %s'; docker exec %s bash -lc 'cat %s'"
           % (b64, C, CONF, C, CONF), 300)
print(o)
if e.strip():
    print('ERR', e[:300])

ensure_running()

print('[2] 重启 serve', flush=True)
ssh("docker exec %s bash -lc 'pkill -f \"[s]erve/server.py\"; sleep 2; pkill -f \"[s]trata --serve\"; sleep 4; echo killed'"
    % C, 300)
o, _ = ssh("docker exec -d %s bash -lc 'cd /src && setsid nohup python3 serve/server.py --engine strata "
           "--config %s --port 8090 > /data/serve-run.log 2>&1 < /dev/null'; sleep 5; "
           "docker exec %s bash -lc 'ps -eo pid,args | grep -c \"[s]erve/server.py\"'" % (C, CONF, C), 300)
print('  server.py 进程数 =', o.strip().splitlines()[-1:])

print('[3] 等就绪（HTTP 探针）', flush=True)
ready = False
for i in range(40):
    time.sleep(20)
    cmd = ("docker exec " + C + " bash -lc 'curl -s -o /dev/null -w \"%{http_code}\" "
           "http://127.0.0.1:8090/v1/models; echo; tail -1 /data/serve-run.log 2>/dev/null'")
    o, _ = ssh(cmd, 120)
    lines = o.strip().splitlines()
    code = (lines or [''])[0].strip()
    tail = (lines or ['', ''])[-1]
    print('  [%3ds] http=%s  %s' % ((i + 1) * 20, code, tail[:100]), flush=True)
    if code == '200':
        ready = True
        break
if not ready:
    o, _ = ssh("docker exec %s bash -lc 'tail -25 /data/serve-run.log; echo ---; tail -20 %s'" % (C, LOG), 300)
    print(o[-3000:])
    raise SystemExit('NOT READY')

o, _ = ssh("docker exec %s bash -lc 'grep -E \"expert cache [0-9]+ slots|resident RAM mode|VRAM free|session is up|kv\" %s | tail -6'" % (C, LOG), 300)
print('  启动关键行:'); print(o)

print('[4] 实测（与之前完全同一脚本）', flush=True)
o, _ = ssh('docker exec %s python3 -u /data/bench_ver.py ctx262_k8v4 2>&1' % C, 3600)
print(o)
