# -*- coding: utf-8 -*-
"""W709 步21：出配置 + 部署 + 重启 + 复验（正确探针版）"""
import hashlib, os, subprocess, sys, time
PY = sys.executable
HERE = r'D:/strata166/params'
GEN = os.path.join(HERE, 'generated', 'strata-ud-iq4_xs.json')
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

r = subprocess.run([PY, '-u', os.path.join(HERE, 'gen_config.py'), '--write'],
                   capture_output=True, text=True, encoding='utf-8')
print('[1] gen_config rc =', r.returncode)
print(r.stdout[-700:])
assert r.returncode == 0
gb = open(GEN, 'rb').read()
print('[1] generated %d B md5=%s CR=%d' % (len(gb), hashlib.md5(gb).hexdigest(), gb.count(b'\r')))
assert gb.count(b'\r') == 0 and not gb.startswith(b'\xef\xbb\xbf')

ok, size, md5, det = _sshutil.push_b64(GEN, '/home/albus/strata166/params/generated/strata-ud-iq4_xs.json')
print('[2] push staging ok=%s size=%s md5=%s' % (ok, size, md5))

DEPLOY = r'''
set -u
LIVE=/home/albus/strata166/data/strata-ud-iq4_xs.json
STAGE=/home/albus/strata166/params/generated/strata-ud-iq4_xs.json
echo "--- 部署前 ---"; md5sum $LIVE
cp -f $LIVE $LIVE.bak_w709b_$(date +%Y%m%d_%H%M%S)
cp -f $STAGE $LIVE; echo "cp_rc=$?"
a=$(md5sum $STAGE | cut -d' ' -f1); b=$(md5sum $LIVE | cut -d' ' -f1)
[ "$a" = "$b" ] && echo "MD5_MATCH=1" || echo "MD5_MATCH=0"
echo "--- 新旋钮各出现次数（应各 1）---"
grep -c -- '--pcie-frac' $LIVE; grep -c -- '--spec-min-p' $LIVE; grep -c -- '--prompt-cache-every' $LIVE
docker restart -t 30 strata166-402 >/dev/null 2>&1; echo "restart_rc=$?"
'''
rc, out, err = _sshutil.run_remote(DEPLOY, timeout=400, host='192.168.50.166')
print(out)
if err.strip():
    print('STDERR:', err[:400])

ready = False
for i in range(30):
    time.sleep(10)
    rc, out, _ = _sshutil.run_remote(
        "docker exec strata166-402 bash -lc 'curl -s -m 6 -o /dev/null -w http=%{http_code} "
        "http://127.0.0.1:8090/v1/models; echo' 2>/dev/null", timeout=90, host='192.168.50.166')
    code = (out.split('http=')[-1].strip().splitlines() or [''])[0] if 'http=' in out else ''
    print('  [%3ds] http=%s' % ((i + 1) * 10, code))
    if code == '200':
        ready = True
        break
print('[3] ready =', ready)
if ready:
    r = subprocess.run([PY, '-u', os.path.join(HERE, 'verify_config.py')],
                       capture_output=True, text=True, encoding='utf-8')
    print('[4] verify rc =', r.returncode)
    print(r.stdout)
