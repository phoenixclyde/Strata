# -*- coding: utf-8 -*-
"""W709 通用单变量交错 A/B：A=现行 config，B=现行 + 一处改动。

用法：
  python _w726_ab.py --prefill auto:16384
  python _w726_ab.py env:STRATA_PREFILL_CPU_SHARE=auto
判定线（技能 §7.8）：预填分辨力 1.5%，解码 11.6~13.0% => 只有中位改善超过对应分辨力才算事实变化。
"""
import base64, json, os, subprocess, sys, time

sys.stdout.reconfigure(encoding='utf-8')
KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
W = '/home/albus/strata166/w709'
LIVE = '/home/albus/strata166/data/strata-ud-iq4_xs.json'
C = 'strata166-402'
ROUNDS = 2


def ssh(sc, t=3600):
    b = base64.b64encode(sc.encode('utf-8')).decode('ascii')
    r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                        '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                       input=b.encode('ascii'), capture_output=True, timeout=t)
    return r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


def sh(cmd, t=600, loud=False):
    o, e = ssh(cmd, t)
    if loud:
        print(o.rstrip(), flush=True)
    return o


def wait_ready(label, max_s=420):
    for i in range(max_s // 10):
        time.sleep(10)
        o = sh("docker exec %s bash -lc 'curl -s -m 6 -o /dev/null -w http=%%{http_code} "
               "http://127.0.0.1:8090/v1/models; echo' 2>/dev/null" % C, 60)
        code = o.strip().split('http=')[-1].strip().splitlines()[0] if 'http=' in o else ''
        print('  [%s %3ds] http=%s' % (label, (i + 1) * 10, code), flush=True)
        if code == '200':
            return True
    return False


def main():
    spec = sys.argv[1]
    # 注意：本机 shim 会把形如 /data/x.py 的参数转成 Windows 路径 => 只传短记号，路径在脚本内拼
    tok = sys.argv[2] if len(sys.argv) > 2 else 'ver'
    BENCH, BENCHARG = {
        'prefix': ('/data/bench_prefix.py', ''),        # 18,083 token（3 chunk）
        'prefix150': ('/data/bench_prefix.py', '150'),  # 6,833 token（<1 chunk）
        'prefix220': ('/data/bench_prefix.py', '220'),  # ~10,000 token（1~2 chunk 之间）
        'ver': ('/data/bench_ver.py', ''),
    }.get(tok, (tok, ''))
    if spec.startswith('env:'):
        k, v = spec[4:].split('=', 1)
        kind, label = 'ENV', '%s=%s' % (k, v)
    elif spec.endswith('=__FLAG__'):
        k, v = spec[:-len('=__FLAG__')], '__FLAG__'
        kind, label = 'CLI', '%s (flag)' % k
    else:
        k, v = spec.split('=', 1)
        kind, label = 'CLI', '%s %s' % (k, v)
    print('### 单变量 A/B：%s  %s   bench=%s' % (kind, label, BENCH), flush=True)

    gen = r'''
import json, io, sys
W = '%s'; LIVE = '%s'
kind, k, v = sys.argv[1], sys.argv[2], sys.argv[3]
A = json.load(io.open(LIVE, encoding='utf-8'))
B = json.loads(json.dumps(A))
if kind == 'CLI':
    a = B['args']
    if v == '__FLAG__':
        if k not in a:
            a.append(k)
    elif k in a:
        a[a.index(k) + 1] = v
    else:
        a += [k, v]
else:
    e = B.setdefault('env', {})
    e[k] = v
io.open(W + '/cfg_A.json', 'w', encoding='utf-8', newline='').write(json.dumps(A, indent=1) + '\n')
io.open(W + '/cfg_B.json', 'w', encoding='utf-8', newline='').write(json.dumps(B, indent=1) + '\n')
print('A args =', ' '.join(A['args']))
print('B args =', ' '.join(B['args']))
print('A env  =', A.get('env'))
print('B env  =', B.get('env'))
''' % (W, LIVE)
    b64 = base64.b64encode(gen.encode('utf-8')).decode('ascii')
    sh("printf '%%s' '%s' | base64 -d > %s/_genAB2.py" % (b64, W), 120)
    sh("python3 %s/_genAB2.py %s %s '%s'" % (W, kind, k, v), 120, loud=True)
    d = sh("diff <(python3 -c \"import json,sys;print(json.dumps(json.load(open('%s/cfg_A.json')),indent=1,sort_keys=True))\") "
           "<(python3 -c \"import json,sys;print(json.dumps(json.load(open('%s/cfg_B.json')),indent=1,sort_keys=True))\")" % (W, W), 60)
    ndiff = len([x for x in d.splitlines() if x.startswith(('<', '>'))])
    print('### A/B 差异行数 = %d（应恰为 2：一行 < 一行 >）' % ndiff, flush=True)

    arms = [(t, c) for _ in range(ROUNDS) for t, c in (('A', 'cfg_A.json'), ('B', 'cfg_B.json'))]
    for rnd, (tag, cfg) in enumerate(arms, 1):
        print('\n' + '#' * 68)
        print('# ROUND %d  ARM %s' % (rnd, tag))
        print('#' * 68, flush=True)
        sh('cp -f %s/%s %s && md5sum %s' % (W, cfg, LIVE, LIVE), 120, loud=True)
        sh('docker restart -t 30 %s >/dev/null 2>&1; echo restart_rc=$?' % C, 300, loud=True)
        if not wait_ready('%s-r%d' % (tag, rnd)):
            print('  [!!] 未就绪', flush=True)
            continue
        print(sh('docker exec %s python3 -u %s %s-r%d %s 2>&1' % (C, BENCH, tag, rnd, BENCHARG), 3600).rstrip(), flush=True)

    print('\n### 收尾：恢复为 register 生成的 config')
    sh('cp -f /home/albus/strata166/params/generated/strata-ud-iq4_xs.json %s && md5sum %s' % (LIVE, LIVE), 120, loud=True)
    sh('docker restart -t 30 %s >/dev/null 2>&1' % C, 300)
    print('restored_ready =', wait_ready('restore'))
    print('DONE')


if __name__ == '__main__':
    main()
