# -*- coding: utf-8 -*-
"""W709 步14：出配置 + 部署（含断言）+ 重启 + 复验"""
import base64, hashlib, io, os, subprocess, sys, time

PY = sys.executable
HERE = r'D:/strata166/params'
GEN = os.path.join(HERE, 'generated', 'strata-ud-iq4_xs.json')
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

# ---------- [1] 证据归档到 166 ----------
src = r'D:/workbuddy/_z_rk81/_w709_calib_out.json'
b = open(src, 'rb').read()
b64 = base64.b64encode(b).decode('ascii')
sc = ("mkdir -p /home/albus/strata166/params/evidence\n"
      "printf '%%s' '%s' | base64 -d > /home/albus/strata166/params/evidence/w709_calib_out.json\n"
      "md5sum /home/albus/strata166/params/evidence/w709_calib_out.json\n") % b64
rc, out, err = _sshutil.run_remote(sc, timeout=200, host='192.168.50.166')
print('[1] 证据归档 md5(166) =', out.strip().split()[0] if out.strip() else '?',
      '| md5(local) =', hashlib.md5(b).hexdigest())

# ---------- [2] 生成 config ----------
r = subprocess.run([PY, '-u', os.path.join(HERE, 'gen_config.py'), '--write'],
                   capture_output=True, text=True, encoding='utf-8')
print('[2] gen_config rc =', r.returncode)
print(r.stdout[-900:])
if r.returncode != 0:
    print(r.stderr[-800:]); raise SystemExit(1)

gb = open(GEN, 'rb').read()
print('[2] generated: %d B md5=%s CR=%d' % (len(gb), hashlib.md5(gb).hexdigest(), gb.count(b'\r')))
assert gb.count(b'\r') == 0

# ---------- [3] 推 + 部署（断言） ----------
ok, size, md5, det = _sshutil.push_b64(GEN, '/home/albus/strata166/params/generated/strata-ud-iq4_xs.json')
print('[3] push staging ok=%s size=%s md5=%s' % (ok, size, md5))

DEPLOY = r'''
set -u
LIVE=/home/albus/strata166/data/strata-ud-iq4_xs.json
STAGE=/home/albus/strata166/params/generated/strata-ud-iq4_xs.json
echo "--- 部署前 LIVE md5 ---"; md5sum $LIVE
cp -f $LIVE $LIVE.bak_w709_$(date +%Y%m%d_%H%M%S)
echo "--- 推 ---"
cp -f $STAGE $LIVE; echo "cp_rc=$?"
echo "--- 部署后 LIVE md5 ---"; md5sum $LIVE
echo "--- 断言：两处 md5 必须相等 ---"
a=$(md5sum $STAGE | cut -d' ' -f1); b=$(md5sum $LIVE | cut -d' ' -f1)
[ "$a" = "$b" ] && echo "MD5_MATCH=1" || echo "MD5_MATCH=0"
echo "--- 断言：新旋钮在 config 里恰好各 1 次 ---"
grep -c -- '--pcie-frac' $LIVE
grep -c -- '--spec-min-p' $LIVE
echo "--- 重启 ---"
docker restart -t 30 strata166-402 >/dev/null 2>&1; echo "restart_rc=$?"
'''
rc, out, err = _sshutil.run_remote(DEPLOY, timeout=400, host='192.168.50.166')
print(out)
if err.strip():
    print('STDERR:', err[:400])

# ---------- [4] 等就绪 ----------
ready = False
for i in range(30):
    time.sleep(10)
    rc, out, _ = _sshutil.run_remote(
        "docker exec strata166-402 bash -lc 'curl -s -m 6 -o /dev/null -w \"%%{http_code}\" "
        "http://127.0.0.1:8090/v1/models; echo' 2>/dev/null", timeout=90, host='192.168.50.166')
    code = (out.strip().splitlines() or [''])[0].strip()
    print('  [%3ds] http=%s' % ((i + 1) * 10, code))
    if code == '200':
        ready = True
        break
print('[4] ready =', ready)

# ---------- [5] 复验 ----------
if ready:
    r = subprocess.run([PY, '-u', os.path.join(HERE, 'verify_config.py')],
                       capture_output=True, text=True, encoding='utf-8')
    print('[5] verify rc =', r.returncode)
    print(r.stdout)
