# -*- coding: utf-8 -*-
"""上下文优化实测：ctx × KV 精度 × KV 驻留 的组合，测「上下文换来的显存代价」与预填速度。

背景：模型训练窗口 262144，现用 131072。KV 有 int8(1056 B/cell) / k8v4(816 B/cell，K 仍精确) / q4_0(int8 的一半)。
一次性 generate 模式：读 `expert cache N slots`（代价币种）+ `VRAM free` + `prefill tok/s`。
"""
import base64, os, re, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
C = 'strata166-401'

BASE = ('--pack /data/packs/ud-iq4_xs --tokens-file /data/probe_tok.txt --max-new 4 '
        '--native /weights/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf '
        '--spec 4 --spec-min-p 0.5 --resident-budget-gib 76 '
        '--expert-profile /src/data/expert-profile.bin --expert-cache auto --prefill auto --stats')

ARMS = [
    ('ctx131_int8（现状）',      '--max-context 131072 --kv int8'),
    ('ctx262_int8',              '--max-context 262144 --kv int8'),
    ('ctx262_k8v4',              '--max-context 262144 --kv k8v4'),
    ('ctx262_q4_0',              '--max-context 262144 --kv q4_0'),
    ('ctx131_k8v4',              '--max-context 131072 --kv k8v4'),
    ('ctx262_int8_kvres32768',   '--max-context 262144 --kv int8 --kv-resident 32768'),
]


def ssh(sc, t=1800):
    b = base64.b64encode(sc.encode('utf-8')).decode('ascii')
    r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                        '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                       input=b.encode('ascii'), capture_output=True, timeout=t)
    return r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


PAT = ('expert cache [0-9]+ slots|MiB of VRAM free|prefill |do not fit|needs --|invalid|'
       'not supported|too large|exceeds|KV|kv-')

print('### 先停 serve 腾出显存', flush=True)
ssh("docker exec %s bash -lc 'pkill -f \"[s]erve/server.py\"; sleep 2; pkill -f \"[s]trata --serve\"; sleep 3; "
    "ps -eo pid,args | grep -c \"[s]trata\"' || true" % C, 300)

results = []
for label, args in ARMS:
    print()
    print('=' * 80)
    print('### %s   %s' % (label, args))
    print('=' * 80, flush=True)
    t0 = time.time()
    o, e = ssh("docker exec %s bash -lc 'cd /src && ./build-906/strata %s %s 2>&1 | grep -E \"%s\" | head -20'"
               % (C, BASE, args, PAT), 1800)
    dt = time.time() - t0
    print(o.strip() if o.strip() else '(无输出)')
    if e.strip():
        print('STDERR', e[:300])
    results.append((label, o, dt))
    print('  -> %.0fs' % dt)

print()
print('=' * 80)
print('### 汇总')
print('=' * 80)
print('%-26s %8s %10s %12s' % ('Arm', 'slots', 'VRAMfree', 'prefill tok/s'))
print('-' * 62)
for label, o, dt in results:
    m_slots = re.search(r'expert cache (\d+) slots', o)
    m_free = re.search(r'([\d.]+) MiB of VRAM free', o)
    m_tok = re.search(r'prefill 16383 tokens in \d+ chunks, [\d.]+ ms \(([\d.]+) tok/s\)', o)
    print('%-26s %8s %10s %12s' % (
        label,
        m_slots.group(1) if m_slots else '-',
        m_free.group(1) if m_free else '-',
        m_tok.group(1) if m_tok else '**失败**'))
