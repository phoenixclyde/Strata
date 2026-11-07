# -*- coding: utf-8 -*-
"""W709 步10：校准结果的独立复核 —— 交错 A/B（baseline vs baseline+calibrated）

判据（技能 §7.8）：本机同臂内解码极差 11.6~13.0%，预填 1.4%。
  => 只有"交错重复测量下的中位改善"超过该分辨力，才算事实上的变化。
设计：同一容器（strata166-402）换 config 重启，A/B/A/B 交错（每臂 2 轮，共 4 次重启），
      每轮跑 /data/bench_ver.py（3 预填 + 3 解码）。唯一变量 = config 的 args。
用法：python _pr131_confirm.py <calib_out.json>     # 本地路径
"""
import base64, json, os, subprocess, sys, time

sys.stdout.reconfigure(encoding='utf-8')
KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'
W = '/home/albus/strata166/w709'
LIVE = '/home/albus/strata166/data/strata-ud-iq4_xs.json'
C = 'strata166-402'


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
    return o, e


def wait_ready(label, max_s=420):
    for i in range(max_s // 10):
        time.sleep(10)
        o, _ = sh('docker exec %s bash -lc \'curl -s -m 6 -o /dev/null -w "%%{http_code}" '
                  'http://127.0.0.1:8090/v1/models; echo\' 2>/dev/null' % C, 60)
        code = (o.strip().splitlines() or [''])[0].strip()
        print('  [%s %3ds] http=%s' % (label, (i + 1) * 10, code), flush=True)
        if code == '200':
            return True
    return False


def load_calib(path):
    """校准的 stdout = 引擎前言 + JSON。取从第一个独占一行的 '{' 到末尾。"""
    raw = open(path, encoding='utf-8').read()
    lines = raw.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == '{':
            return json.loads('\n'.join(lines[i:]))
    return json.loads(raw)          # 兜底：本来就是纯 JSON


def main():
    calib = load_calib(sys.argv[1])
    settings = calib.get('settings') or {}
    print('校准给出的 settings =', json.dumps(settings, ensure_ascii=False))
    print('校准自报 report =', json.dumps(calib.get('report', {}), ensure_ascii=False)[:1200])

    # ---- 用同一个变换器生成 cfg_B（远程，避免手抄 args）----
    gen = r'''
import json, io, sys
W = '/home/albus/strata166/w709'
LIVE = '/home/albus/strata166/data/strata-ud-iq4_xs.json'
settings = json.loads(io.open(W + '/calib_settings.json', encoding='utf-8').read())
A = json.load(io.open(LIVE, encoding='utf-8'))
B = json.loads(json.dumps(A))
args = B['args']
for flag, val in settings.items():
    if flag in args:
        args[args.index(flag) + 1] = str(val)
    else:
        args += [flag, str(val)]
io.open(W + '/cfg_A.json', 'w', encoding='utf-8', newline='').write(json.dumps(A, indent=1) + '\n')
io.open(W + '/cfg_B.json', 'w', encoding='utf-8', newline='').write(json.dumps(B, indent=1) + '\n')
print('A_args_tail =', ' '.join(A['args'][-8:]))
print('B_args_tail =', ' '.join(B['args'][-8:]))
print('ADDED =', [k for k in settings if k not in A['args']])
'''
    b64 = base64.b64encode(gen.encode('utf-8')).decode('ascii')
    sh("printf '%%s' '%s' | base64 -d > %s/_genAB.py" % (b64, W), 120)
    # settings 落远程
    sb = base64.b64encode(json.dumps(settings, ensure_ascii=False).encode('utf-8')).decode('ascii')
    sh("printf '%%s' '%s' | base64 -d > %s/calib_settings.json" % (sb, W), 120)
    sh('python3 %s/_genAB.py' % W, 120, loud=True)

    if not settings:
        print('\n>>> 校准结果 = 无任何改动（全部未超过 3% 门槛）=> 无需 A/B，基线即最优。')
        return

    print('\n' + '=' * 72)
    print('交错 A/B 开始：A=baseline(register)  B=baseline+calibrated')
    print('=' * 72, flush=True)
    arms = [('A', 'cfg_A.json'), ('B', 'cfg_B.json'), ('A', 'cfg_A.json'), ('B', 'cfg_B.json')]
    for rnd, (tag, cfg) in enumerate(arms, 1):
        print('\n' + '#' * 70)
        print('# ROUND %d  ARM %s  cfg=%s' % (rnd, tag, cfg))
        print('#' * 70, flush=True)
        sh('cp -f %s/%s %s && md5sum %s' % (W, cfg, LIVE, LIVE), 120, loud=True)
        sh('docker restart -t 30 %s >/dev/null 2>&1; echo restarted_rc=$?' % C, 300, loud=True)
        if not wait_ready('%s-r%d' % (tag, rnd)):
            print('  [!!] 未就绪，跳过该臂', flush=True)
            continue
        o, _ = ssh('docker exec %s python3 -u /data/bench_ver.py %s-r%d 2>&1' % (C, tag, rnd), 3600)
        print(o.rstrip(), flush=True)
        o, _ = ssh('grep -E "prompt [0-9]+ tokens" /data/strata-ud-iq4_xs.log | tail -4 | cut -c1-150', 180)
        print('  [engine] ' + o.strip().replace('\n', '\n  [engine] '), flush=True)

    print('\n' + '=' * 72)
    o, _ = sh('grep "SUMMARY" /dev/null; echo', 60)
    print('DONE')


if __name__ == '__main__':
    main()
