# -*- coding: utf-8 -*-
"""镜像产出后的验收：sha256 校验收尾 + 起容器 + 容器内确认能认卡/引擎可跑。"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
echo "=== 1) 权重 sha256 全量校验结果 ==="
cat /home/albus/strata166/logs/verify-weights.log
echo
echo "=== 2) 镜像里关键产物 ==="
docker run --rm --entrypoint bash strata-gfx906:0.1.39 -lc '
  ls -l /src/build-906/strata
  echo "--- 版本/帮助前 5 行 ---"
  /src/build-906/strata --help 2>&1 | head -5
  echo "--- 是否带 K-quant MMQ 符号（STRATA_MMQ_KQUANTS）---"
  ( nm -C /src/build-906/strata 2>/dev/null | grep -ci kquant ) 2>/dev/null || echo "   (nm 不可用)"
  echo "--- tools/ 与 serve/ 在位 ---"
  ls /src/tools/iq_pack.py /src/serve/server.py /src/third_party/llama.cpp/gguf-py/gguf/__init__.py 2>&1
  echo "--- python 依赖 ---"
  python3 -c "import numpy,jinja2,psutil;print(\"deps ok\", numpy.__version__)"
' 2>&1 | sed 's/^/  /'
echo
echo "=== 3) 起容器（只读挂权重 + 数据目录 + 8090）==="
docker rm -f strata166 2>/dev/null | head -1
mkdir -p /home/albus/strata166/data
docker run -d --name strata166 \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  --ipc=host --ulimit memlock=-1 \
  -v /home/albus/strata166/weights:/weights:ro \
  -v /home/albus/strata166/data:/data \
  -p 8090:8090 \
  strata-gfx906:0.1.39 sleep infinity 2>&1
sleep 3
docker ps --filter name=strata166 --format '{{.Names}}|{{.Status}}|{{.Ports}}'
echo
echo "=== 4) 容器内能否认到 gfx906 ==="
docker exec strata166 bash -lc 'rocminfo 2>&1 | grep -E "^  Name:|gfx|Compute Unit|Wavefront" | head -12; echo "--- rocm-smi ---"; rocm-smi --showmeminfo vram 2>&1 | head -8'
echo
echo "=== 5) /dev/kfd /dev/dri 在容器内 ==="
docker exec strata166 ls -l /dev/kfd /dev/dri 2>&1 | head
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=30',
       '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=900)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:600])
