# -*- coding: utf-8 -*-
"""取证：两套权重测试各自用的引擎版本（镜像 ID + 引擎自报版本行）。"""
import base64, os, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SC = r'''
set +e
echo "=== 镜像（含 ID，可追溯）==="
docker images --no-trunc --format '{{.Repository}}:{{.Tag}} | {{.ID}} | {{.Size}} | {{.CreatedSince}}' | grep -i strata
echo
echo "=== 当前在跑的容器用的是哪个镜像 ==="
docker inspect -f '{{.Name}} image={{.Config.Image}} imageID={{.Image}}' strata166-401 strata166 2>&1
echo
echo "=== 引擎自报版本（两套权重的日志各取最后一条 session is up）==="
echo "--- UD-Q4_K_XL 日志: /data/strata-ud-q4_k_xl.log ---"
docker exec strata166-401 bash -lc 'grep -n "engine 0" /data/strata-ud-q4_k_xl.log 2>/dev/null | tail -3'
echo "--- UD-IQ4_XS 日志: /data/strata-ud-iq4_xs.log ---"
docker exec strata166-401 bash -lc 'grep -n "engine 0" /data/strata-ud-iq4_xs.log 2>/dev/null | tail -3'
echo
echo "=== 引擎二进制的路径与构建时间（0.1.40.1 镜像内）==="
docker exec strata166-401 bash -lc 'ls -l /src/build-906/strata; grep -m1 -E "STRATA_HIP_GFX906|project" /src/CMakeLists.txt | head -2; grep -m1 "VERSION" /src/CMakeLists.txt'
echo
echo "=== 两份配置的差异（应只有 pack/native/model/log/tokenizer）==="
docker exec strata166-401 bash -lc 'diff <(python3 -c "import json;print(json.dumps(json.load(open(chr(47)+\"data/strata-ud-q4_k_xl.json\")),indent=1,sort_keys=True))") <(python3 -c "import json;print(json.dumps(json.load(open(chr(47)+\"data/strata-ud-iq4_xs.json\")),indent=1,sort_keys=True))")'
'''
b = base64.b64encode(SC.encode('utf-8')).decode('ascii')
r = subprocess.run([SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                    '-o', 'ServerAliveInterval=30', '-i', KEY, HOST, 'base64 -d | bash'],
                   input=b.encode('ascii'), capture_output=True, timeout=300)
print(r.stdout.decode('utf-8', 'replace'))
e = r.stderr.decode('utf-8', 'replace')
if e.strip():
    print('ERR', e[:400])
