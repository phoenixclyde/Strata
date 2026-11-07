# -*- coding: utf-8 -*-
# [过期 2026-10-09 标注] 历史一次性脚本（W708c 批次A 扫描）。依赖 D:/strata166/... 与 routeK 旧区，
#   现行工具链 = gen_config.py / verify_config.py（已自包含）。本件仅存档，勿再运行。
"""批次 A：只收**行为中性**的两项，走完整固化闭环。

  P20 --expert-profile-save  ：只写文件、不改运行时行为 -> 可直接收
  P11 env 写进 config        ：把 docker -e 的 HSA_OVERRIDE_GFX_VERSION 落进 config，使其自包含 -> 可直接收

流程：改 register -> gen_config --write -> 备份+推 166 -> 重启 -> verify_config 复验
"""
import io, os, sys, time, re, json, shutil
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
sys.stdout.reconfigure(encoding='utf-8')
import _sshutil

P = r'D:/strata166/params/PARAM_REGISTER.tsv'
GEN = r'D:/strata166/params/generated/strata-ud-iq4_xs.json'
HOST = '192.168.50.166'
LIVE = '/home/albus/strata166/data/strata-ud-iq4_xs.json'
C = 'strata166-402'

# ---------- [1] 改 register：P20 CANDIDATE -> ADOPTED ----------
t = io.open(P, encoding='utf-8-sig').read()
lines = t.splitlines()
done = 0
for i, ln in enumerate(lines):
    f = ln.split('\t')
    if f and f[0] == 'P20' and f[5] == 'CANDIDATE':
        f[5] = 'ADOPTED'
        f[10] = '批次A：行为中性（仅写文件）；已收'
        lines[i] = '\t'.join(f)
        done += 1
if done not in (0, 1):
    raise SystemExit('P20 状态改写异常 done=%d' % done)
if done == 0:
    print('[1] register: P20 已是 ADOPTED（幂等跳过）')
else:
    open(P, 'wb').write(('\n'.join(lines) + '\n').encode('utf-8'))
    print('[1] register: P20 -> ADOPTED')

# ---------- [2] 生成 ----------
import subprocess
r = subprocess.run([sys.executable, '-u', r'D:/strata166/params/gen_config.py', '--write'],
                   capture_output=True)
print('[2] gen_config rc=%d' % r.returncode)
if r.returncode:
    print(r.stdout.decode('utf-8', 'replace')[-1500:]); print(r.stderr.decode('utf-8', 'replace')[-800:])
    raise SystemExit(2)
new = io.open(GEN, encoding='utf-8').read()
cfg = json.loads(new)
print('[2] 生成 args =', cfg['args'])
print('    env =', cfg.get('env'))

# ---------- [3] 166：建目录、备份、推 config ----------
rc, out, err = _sshutil.run_remote(
    'mkdir -p /home/albus/strata166/data/profiles && ls -ld /home/albus/strata166/data/profiles', timeout=120, host=HOST)
print('[3] profiles 目录:', out.strip().splitlines()[-1] if out.strip() else err[:200])

ts = time.strftime('%Y%m%d_%H%M%S')
rc, out, err = _sshutil.run_remote('cp -a %s %s.bak_%s && echo backup_ok' % (LIVE, LIVE, ts), timeout=120, host=HOST)
print('    备份:', out.strip()[:120])

ok, size, md5, det = _sshutil.push_b64(GEN, '/tmp/_cfg_new.json')
print('    推送新 config: ok=%s size=%s md5=%s' % (ok, size, md5))
rc, out, err = _sshutil.run_remote('cp -a /tmp/_cfg_new.json %s && md5sum %s && rm -f /tmp/_cfg_new.json' % (LIVE, LIVE),
                                   timeout=120, host=HOST)
print('    落盘:', out.strip()[:200])

# ---------- [4] 重启并等就绪 ----------
rc, out, err = _sshutil.run_remote('docker restart %s >/dev/null 2>&1; echo restart_rc=$?' % C, timeout=300, host=HOST)
print('[4] 重启:', out.strip()[:80])
ready = False
for i in range(24):
    time.sleep(10)
    rc, out, _ = _sshutil.run_remote(
        'docker exec %s bash -lc "curl -s -m 5 -o /dev/null -w %%{http_code} http://127.0.0.1:8090/v1/models; echo" 2>/dev/null'
        % C, timeout=90, host=HOST)
    code = (out.strip().splitlines() or [''])[0].strip()
    print('    [%3ds] http=%s' % ((i + 1) * 10, code))
    if code == '200':
        ready = True
        break
print('    就绪 =', ready)

# ---------- [5] 复验 ----------
print('[5] 固化复验：')
r = subprocess.run([sys.executable, '-u', r'D:/strata166/params/verify_config.py'], capture_output=True)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print(r.stderr.decode('utf-8', 'replace')[-600:])
print('verify rc =', r.returncode)
print('备份 ts =', ts)
