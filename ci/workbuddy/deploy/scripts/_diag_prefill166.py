# -*- coding: utf-8 -*-
"""预填瓶颈判定性诊断：一次性 generate 模式拿分解行 + PLE/CPU池 消融。

产出（每臂一行关键分解）：
  prefill N tokens in C chunks, X ms (Y tok/s); experts streamed S (D by DMA, host H ms), resident R; PLE P ms
消融：
  base            现状
  no_ple          --no-ple        （PLE 完全不参与 ⇒ PLE 的真实代价）
  no_pool         --no-pool       （GPU-only 地板 ⇒ CPU 专家池的代价）
  auto32768       --prefill auto:32768
"""
import base64, os, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
C = 'strata166-401'

COMMON = ('--pack /data/packs/ud-iq4_xs '
          '--tokens-file /data/probe_tok.txt --max-new 4 '
          '--native /weights/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf '
          '--spec 4 --spec-min-p 0.5 '
          '--resident-budget-gib 76 --expert-profile /src/data/expert-profile.bin '
          '--expert-cache auto --max-context 131072 --kv int8')
PLE = '/weights/Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf'

ARMS = [
    ('base',      COMMON + ' --prefill auto --stats'),
    ('no_ple',    COMMON + ' --ple-gguf ' + PLE + ' --prefill auto --stats --no-ple'),
    ('no_pool',   COMMON + ' --prefill auto --stats --no-pool'),
    ('auto32768', COMMON + ' --prefill auto:32768 --stats'),
]


def ssh(sc, t=3600):
    b = base64.b64encode(sc.encode('utf-8')).decode('ascii')
    r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                        '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                       input=b.encode('ascii'), capture_output=True, timeout=t)
    return r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


print('[1] 停 serve 腾出 VRAM（一次性模式要独占显存）', flush=True)
o, _ = ssh("docker exec %s bash -lc 'pkill -f \"[s]erve/server.py\"; sleep 2; "
           "pkill -f \"[s]trata --serve\"; sleep 3; ps -eo pid,args | grep -c \"[s]trata\" || true' %s" % (C, C), 300)
print(o)

print('[2] 造 token 文件（16384 个确定伪随机 id，范围 1000..200000）', flush=True)
import random
random.seed(20261007)
ids = [random.randrange(1000, 200000) for _ in range(16384)]
payload = ','.join(map(str, ids))
b64 = base64.b64encode(payload.encode('ascii')).decode('ascii')
o, _ = ssh("echo %s | base64 -d | docker exec -i %s bash -lc 'cat > /data/probe_tok.txt'; "
           "docker exec %s bash -lc 'wc -c /data/probe_tok.txt'" % (b64, C, C), 600)
print(o)

for label, args in ARMS:
    print()
    print('=' * 78)
    print('### ARM %s' % label, flush=True)
    print('=' * 78, flush=True)
    o, e = ssh("docker exec %s bash -lc 'cd /src && ./build-906/strata %s 2>&1 | "
               "grep -E \"prefill |PLE |expert cache|resident RAM|session is up|tok/s|ms/token|token host phases|"
               "total|needs --|requires|invalid\" | head -40'"
               % (C, args), 1800)
    print(o[-3500:])
    if e.strip():
        print('STDERR', e[:600])
