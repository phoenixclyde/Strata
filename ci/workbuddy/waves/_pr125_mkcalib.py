# W709 步4：生成校准专用 config（机器变换，不手抄 args）
import sys
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

GEN = r'''
import json, io, os
P = '/home/albus/strata166/data/strata-ud-iq4_xs.json'
Q = '/home/albus/strata166/data/strata-calib.json'
cfg = json.load(io.open(P, encoding='utf-8'))
# 1) 日志另开（不污染生产日志）
cfg['log'] = '/data/strata-calib.log'
# 2) 端口另开（calibrate 不绑端口，仅为稳妥）
cfg['port'] = 8099
# 3) profile-save 另开（不污染生产学习档）
a = cfg['args']
if '--expert-profile-save' in a:
    a[a.index('--expert-profile-save') + 1] = '/data/profiles/calib-learned.bin'
cfg['model_name'] = cfg['model_name'] + '-calib'
io.open(Q, 'w', encoding='utf-8', newline='').write(json.dumps(cfg, indent=1, ensure_ascii=False) + '\n')
print('WROTE', Q, os.path.getsize(Q), 'B')
print('--- 与生产 config 的差异（逐键） ---')
prod = json.load(io.open(P, encoding='utf-8'))
for k in sorted(set(prod) | set(cfg)):
    if prod.get(k) != cfg.get(k):
        print('  %-14s : %r -> %r' % (k, prod.get(k), cfg.get(k)))
'''

PUSH = r'''
mkdir -p /home/albus/strata166/w709
python3 - <<'PYEOF'
%s
PYEOF
echo "--- 生成结果 ---"
cat /home/albus/strata166/data/strata-calib.json
'''

import base64
payload = base64.b64encode(GEN.encode('utf-8')).decode('ascii')
import textwrap
sc = ("mkdir -p /home/albus/strata166/w709\n"
      "printf '%%s' '%s' | base64 -d > /home/albus/strata166/w709/_mkcalibcfg.py\n"
      "python3 /home/albus/strata166/w709/_mkcalibcfg.py\n"
      "echo '--- 生成结果 ---'\n"
      "cat /home/albus/strata166/data/strata-calib.json\n") % payload

rc, out, err = _sshutil.run_remote(sc, timeout=200, host='192.168.50.166')
print('rc =', rc)
print(out)
if err.strip():
    print('--- STDERR ---')
    print(err[:600])
