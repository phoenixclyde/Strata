# -*- coding: utf-8 -*-
"""探底座镜像 docker.1ms.run/mixa3607/rocm-gfx906:7.14-complete 的真实构成（现在已在本地）。
目的：写对 Dockerfile —— 有哪些工具、apt 源里哪个是坏的、python/pip 情况。"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
IMG=docker.1ms.run/mixa3607/rocm-gfx906:7.14-complete
echo "=== 镜像信息 ==="
docker image inspect $IMG --format '{{.Id}} | {{.Size}}B | {{.Created}}' 2>&1
echo
echo "=== 容器内探查 ==="
docker run --rm --entrypoint bash $IMG -lc '
  (. /etc/os-release; echo "os=$PRETTY_NAME")
  echo "--- 工具 ---"
  for c in cmake ninja clang clang++ hipcc gcc g++ git python3 python pip pip3 unzip tar sha256sum; do
    printf "  %-10s " $c; command -v $c || echo MISSING
  done
  echo "--- python ---"; python3 -V 2>&1; python3 -c "import sys;print(sys.prefix)" 2>&1
  echo "--- pip ---"; python3 -m pip --version 2>&1 | head -2
  echo "--- rocm ---"; cat /opt/rocm/.info/version 2>/dev/null; /opt/rocm/bin/hipcc --version 2>&1 | head -2
  echo "--- rocm llvm bin ---"; ls /opt/rocm/*/lib/llvm/bin/clang++ /opt/rocm/llvm/bin/clang++ 2>&1 | head
  echo "--- apt 源文件 ---"
  ls -l /etc/apt/sources.list /etc/apt/sources.list.d/ 2>&1
  echo "--- 源内容 ---"
  cat /etc/apt/sources.list 2>/dev/null | grep -v "^#" | grep -v "^$" | head
  for f in /etc/apt/sources.list.d/*; do echo "  [$f]"; grep -v "^#" "$f" | grep -v "^$" | head -5; done
  echo "--- 标记这些源是否与 gfx906 相关 ---"
  grep -rl "arkprojects" /etc/apt/ 2>/dev/null
  echo "--- 预装 python 包 ---"
  python3 -c "import numpy; print(\"numpy\", numpy.__version__)" 2>&1 | head -2
' 2>&1 | sed 's/^/  /'
echo
echo "=== 磁盘 ==="; df -h / | tail -1
echo "=== docker system df ==="; docker system df 2>&1 | head -6
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=900)
print(r.stdout.decode('utf-8', 'replace'))
if r.stderr.strip():
    print('ERR', r.stderr.decode('utf-8', 'replace')[:400])
