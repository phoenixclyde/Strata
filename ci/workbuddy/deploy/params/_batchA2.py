# -*- coding: utf-8 -*-
# [过期 2026-10-09 标注] 历史一次性脚本（W708c 批次A 扫描）。依赖 D:/strata166/... 与 routeK 旧区，
#   现行工具链 = gen_config.py / verify_config.py（已自包含）。本件仅存档，勿再运行。
"""批次 A 第二步：修正权限问题后用 sudo 重推 config，重启并复验（每步都有断言）。"""
import io, os, sys, time, subprocess, json, hashlib
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
sys.stdout.reconfigure(encoding='utf-8')
import _sshutil

GEN = r'D:/strata166/params/generated/strata-ud-iq4_xs.json'
LIVE = '/home/albus/strata166/data/strata-ud-iq4_xs.json'
HOST = '192.168.50.166'
C = 'strata166-402'


def sh(cmd, t=200, tag=''):
    rc, out, err = _sshutil.run_remote(cmd, timeout=t, host=HOST)
    print('   [%s] rc=%s out=%s%s' % (tag, rc, (out.strip().splitlines() or [''])[-1][:150],
                                      (' ERR=' + err.strip()[:120]) if err.strip() else ''))
    return rc, out, err


# ---------- [1] 推送（sudo + md5 双端断言） ----------
new_b = open(GEN, 'rb').read()
md5_new = hashlib.md5(new_b).hexdigest()
print('[1] 本地生成件 %d B md5=%s' % (len(new_b), md5_new))
ok, size, md5, det = _sshutil.push_b64(GEN, '/tmp/_cfg_new.json')
assert ok and md5 == md5_new, 'push_b64 失败 ok=%s md5=%s' % (ok, md5)
print('   push_b64 ok=%s size=%s md5=%s' % (ok, size, md5))

ts = time.strftime('%Y%m%d_%H%M%S')
sh('sudo -n cp -a %s %s.bak_%s && echo BACKUP_OK' % (LIVE, LIVE, ts), tag='backup')
rc, out, err = sh('sudo -n cp -a /tmp/_cfg_new.json %s && echo CP_OK' % LIVE, tag='cp')
assert 'CP_OK' in out, 'cp 未成功（权限？）'
rc, out, err = sh('md5sum %s' % LIVE, tag='md5')
assert md5_new in out, '远端 md5 与本地不符: %s' % out.strip()[:200]
sh('rm -f /tmp/_cfg_new.json', tag='clean')
rc, out, err = sh('grep -c expert-profile-save %s' % LIVE, tag='grep-newflag')
assert out.strip().endswith('1'), '新 flag 不在 config 里'

# ---------- [2] 重启 ----------
sh('docker restart %s >/dev/null 2>&1; echo RESTART_RC=$?' % C, t=300, tag='restart')
ready = False
for i in range(24):
    time.sleep(10)
    rc, out, _ = _sshutil.run_remote(
        'docker exec %s bash -lc "curl -s -m 5 -o /dev/null -w %%{http_code} http://127.0.0.1:8090/v1/models; echo" 2>/dev/null'
        % C, timeout=90, host=HOST)
    code = (out.strip().splitlines() or [''])[0].strip()
    print('   [ready %3ds] http=%s' % ((i + 1) * 10, code))
    if code == '200':
        ready = True
        break
assert ready, '服务未就绪'

# ---------- [3] 复验 ----------
print()
print('[3] 固化复验：')
r = subprocess.run([sys.executable, '-u', r'D:/strata166/params/verify_config.py'], capture_output=True)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print(r.stderr.decode('utf-8', 'replace')[-500:])
print('verify rc = %d   备份 ts = %s' % (r.returncode, ts))
