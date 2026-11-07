# -*- coding: utf-8 -*-
"""A+B 扫描：官方 MI50 显存腾挪配方 + 预填/池旋钮（一次性 generate 模式，每臂约 1.5-2 分钟）

每臂输出：prefill 行（tok/s + PLE ms + host ms）、ple io 行、CPU 池行。
fail-closed：抽不到 prefill 行就报出该臂的原始错误，不静默跳过。
"""
import base64, os, re, subprocess, sys, time
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
          '--expert-cache auto --max-context 131072 --kv int8 '
          '--prefill auto --stats')

# (标签, 追加参数, 额外环境变量)
ARMS = [
    ('A1_base',           '', ''),
    ('A2_kvres32768',     '--kv-resident 32768', ''),
    ('A3_vramres600',     '--kv-resident 32768 --vram-reserve-mib 600', ''),
    ('A4_arena_mmap',     '--kv-resident 32768 --vram-reserve-mib 600 --pcie-frac 0',
                          'STRATA_ARENA_MMAP=1'),
    ('B1_no_borrow',      '--no-prefill-borrow', ''),
    ('B2_no_split_rows',  '--no-split-rows', ''),
    ('B3_shared_late',    '--shared-late', ''),
    ('B4_pool22',         '--pool-workers 22', ''),
    ('B5_ring256',        '', 'STRATA_PREFILL_RING=256'),
    ('B6_no_pool',        '--no-pool', ''),
]


def ssh(sc, t=3600):
    b = base64.b64encode(sc.encode('utf-8')).decode('ascii')
    r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                        '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                       input=b.encode('ascii'), capture_output=True, timeout=t)
    return r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


PAT = ('prefill |ple io:|the CPU expert pool|pool phases|session is up|'
       'expert cache [0-9]+ slots|resident RAM mode|needs --|requires|invalid|cannot|failed|error')

print('### 清掉占 VRAM 的 serve（一次性模式要独占显存）', flush=True)
ssh("docker exec %s bash -lc 'pkill -f \"[s]erve/server.py\"; sleep 2; pkill -f \"[s]trata --serve\"; sleep 3;"
    " ps -eo pid,args | grep -c \"[s]trata\"' || true" % C, 300)

for label, extra, env in ARMS:
    print()
    print('=' * 80)
    print('### ARM %s    extra=%r   env=%r' % (label, extra, env))
    print('=' * 80, flush=True)
    t0 = time.time()
    cmd = ("docker exec %s bash -lc 'cd /src && %s./build-906/strata %s %s 2>&1 | "
           "grep -E \"%s\" | head -30'" % (C, (env + ' ') if env else '', COMMON, extra, PAT))
    o, e = ssh(cmd, 2400)
    dt = time.time() - t0
    print(o.strip())
    if e.strip():
        print('STDERR', e[:500])
    ok = 'prefill ' in o
    print('  -> 用时 %.0fs   有分解行=%s' % (dt, 'YES' if ok else '**NO**'))
