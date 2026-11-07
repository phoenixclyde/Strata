# -*- coding: utf-8 -*-
"""166：修 mtp-manifest.json 的反斜杠 → 重跑 mtp_pack → mtp_rt"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
echo "=== 1) 修清单里的反斜杠 ==="
docker exec -i strata166 python3 - <<'PYEOF'
import json, pathlib, shutil
p = pathlib.Path('/data/mtp/mtp-manifest.json')
shutil.copy2(str(p), str(p) + '.bak')
m = json.loads(p.read_text())
n = 0
for t in m:
    f = t.get('file', '')
    if '\\' in f:
        t['file'] = f.replace('\\', '/')
        n += 1
p.write_text(json.dumps(m, indent=1))
print('fixed %d of %d entries; sample=%s' % (n, len(m), m[0]['file']))
PYEOF
echo "rc=$?"
echo
echo "=== 2) mtp_pack（q2_0）==="
docker exec strata166 bash -lc 'cd /src && python3 tools/mtp_pack.py --src /data/mtp --experts q2_0 --out /data/mtp/mtp-q2_0.gguf' 2>&1 | tail -20
echo "rc=$?"
docker exec strata166 bash -lc 'ls -l /data/mtp/*.gguf 2>/dev/null'
echo
echo "=== 3) mtp_rt ==="
docker exec strata166 bash -lc 'cd /src && python3 tools/mtp_rt.py --gguf /data/mtp/mtp-q2_0.gguf --out /data/mtp/rt' 2>&1 | tail -20
echo "rc=$?"
echo
echo "=== 4) rt 目录 ==="
docker exec strata166 bash -lc 'ls -l /data/mtp/rt; echo "--- dense.txt 头 5 行 ---"; head -5 /data/mtp/rt/dense.txt 2>/dev/null; echo "--- 行数 ---"; wc -l /data/mtp/rt/dense.txt 2>/dev/null'
echo
echo "=== 5) 磁盘 ==="
df -h / | tail -1
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=1800)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('--- STDERR ---')
    print(r.stderr.decode('utf-8', 'replace')[:800])
