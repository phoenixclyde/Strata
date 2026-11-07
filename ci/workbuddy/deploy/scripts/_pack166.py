# -*- coding: utf-8 -*-
"""166：跑 iq_pack --compat-bf16 出 pack，并写好 serve 配置（首启用小 ctx，先证明能加载）。"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
echo "=== 1) iq_pack --compat-bf16 ==="
docker exec strata166 bash -lc '
cd /src
STRATA_GGUF_PY=/src/third_party/llama.cpp/gguf-py python3 tools/iq_pack.py \
  --gguf /weights/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf \
  --out /data/packs/ud-q4_k_xl --compat-bf16
echo "iq_pack rc=$?"
' 2>&1 | tail -40
echo
echo "=== 2) pack 产物 ==="
docker exec strata166 bash -lc 'ls -l /data/packs/ud-q4_k_xl 2>&1; echo "--- tokenizer ---"; ls /data/packs/ud-q4_k_xl/tokenizer 2>&1; echo "--- index.txt 前 3 行 ---"; head -3 /data/packs/ud-q4_k_xl/index.txt 2>&1'
echo
echo "=== 3) 写 serve 配置 ==="
docker exec strata166 bash -lc 'cat > /data/strata-ud-q4_k_xl.json <<JSONEOF
{
  "exe": "/src/build-906/strata",
  "args": [
    "--pack", "/data/packs/ud-q4_k_xl",
    "--native", "/weights/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf",
    "--resident-budget-gib", "76",
    "--expert-profile", "/src/data/expert-profile.bin", "--expert-cache", "auto",
    "--prefill", "auto", "--spec", "4", "--spec-min-p", "0.5",
    "--max-context", "8192",
    "--kv", "int8"
  ],
  "cwd": "/src",
  "tokenizer": "/data/packs/ud-q4_k_xl/tokenizer",
  "model_name": "qwen3.8-flash-next-ud-q4_k_xl",
  "log": "/data/strata-ud-q4_k_xl.log",
  "host": "0.0.0.0",
  "port": 8090
}
JSONEOF
echo "--- 写入内容 ---"; cat /data/strata-ud-q4_k_xl.json; python3 -c "import json;json.load(open(\"/data/strata-ud-q4_k_xl.json\"));print(\"JSON OK\")"'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=1800)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:800])
