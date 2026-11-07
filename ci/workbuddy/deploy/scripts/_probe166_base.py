# -*- coding: utf-8 -*-
"""166：为「新建一个独立的 Strata gfx906 镜像」盘点可选底座与仓库可达性（只读，不拉不建）。"""
import base64, os, subprocess, time

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
OUT = r'D:\workbuddy_space\2026-10-04-13-25-07\_166_base_probe.txt'

SCRIPT = r'''
set +e
echo "=== A) 本地全部镜像（找 gfx906 / ROCm 底座）==="
docker images --format '{{.ID}}|{{.Repository}}:{{.Tag}}|{{.Size}}|{{.CreatedSince}}' | sort -t'|' -k2
echo
echo "=== B) docker info：存储/构建器/镜像源 ==="
docker info 2>&1 | grep -Ei 'Storage Driver|Docker Root Dir|Cgroup|Buildkit|Registry Mirrors|Server Version' -A2 | head -30
echo
echo "=== C) 候选底座的内部构成（本地可用的）==="
for IMG in mixa3607/vllm-gfx906:0.20.1-rocm-7.2.1-aiinfos docker.1ms.run/mixa3607/llama.cpp-gfx906:v0.5.0-rocm-7.14; do
  echo "---- $IMG"
  docker run --rm --entrypoint bash "$IMG" -lc '
    (. /etc/os-release; echo "  os=$PRETTY_NAME")
    for c in cmake ninja clang clang++ hipcc gcc g++ git python3 pip3; do printf "  %-9s " $c; command -v $c || echo MISSING; done
    ls -d /opt/rocm* 2>&1 | sed "s/^/  /"
    cat /opt/rocm/.info/version 2>/dev/null | sed "s/^/  rocm=/"
    /opt/rocm/bin/hipcc --version 2>&1 | head -3 | sed "s/^/  /"
    ls /opt/rocm/lib/libamdhip64.so* /opt/rocm/lib/libhipblas.so* 2>&1 | sed "s/^/  /"
    for p in /opt/rocm/llvm/bin/clang++ /opt/rocm/core-7.14/lib/llvm/bin/clang++; do
      printf "  %-42s " $p; [ -x $p ] && echo OK || echo MISSING
    done
  ' 2>&1 | head -40
done
echo
echo "=== D) routek-base 的血缘（它的 FROM 是什么）==="
docker image inspect routek-base:gfx906-rocm101-hip716-torch215 --format '{{json .Config.Labels}}' 2>&1 | head -3
docker history --no-trunc --format '{{.CreatedBy}}|{{.Size}}' routek-base:gfx906-rocm101-hip716-torch215 2>&1 | tail -8
echo
echo "=== E) 各镜像源可达性（只做 manifest 探测，不拉）==="
for R in \
  "docker.1ms.run/mixa3607/rocm-gfx906:7.14-complete" \
  "mixa3607/rocm-gfx906:7.14-complete" \
  "docker.1ms.run/library/ubuntu:24.04" \
  "docker.m.daocloud.io/mixa3607/rocm-gfx906:7.14-complete" ; do
  printf '  %-58s ' "$R"
  timeout 45 docker manifest inspect "$R" >/tmp/_mi.json 2>/tmp/_mi.err
  rc=$?
  if [ $rc -eq 0 ]; then echo "OK ($(wc -c </tmp/_mi.json) B manifest)"; else echo "FAIL rc=$rc $(head -c 120 /tmp/_mi.err | tr '\n' ' ')"; fi
done
echo
echo "--- registry 主机直连（curl）---"
for H in https://docker.1ms.run/v2/ https://docker.m.daocloud.io/v2/ https://ibn6uwqj78h0apyas2.xuanyuan.run/v2/ https://registry-1.docker.io/v2/ ; do
  printf '  %-58s ' "$H"; curl -s -o /dev/null -m 10 -w '%{http_code} %{time_total}s\n' "$H" || echo FAIL
done
echo
echo "=== F) 磁盘（镜像会写 /var/lib/docker）==="
df -h / /var/lib/docker 2>&1 | head -6
du -sh /var/lib/docker 2>/dev/null
echo
echo "=== G) 有没有已经存在的 strata 镜像 ==="
docker images --format '{{.Repository}}:{{.Tag}}' | grep -i strata 2>&1 || echo "  (无)"
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY,
       'albus@192.168.50.166', 'base64 -d | bash']
t0 = time.time()
try:
    p = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=900)
    out, err, rc = p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace'), p.returncode
except subprocess.TimeoutExpired as e:
    out, err, rc = (e.stdout or b'').decode('utf-8', 'replace'), 'TIMEOUT', -1
open(OUT, 'w', encoding='utf-8').write('rc=%s %.1fs\n%s\n--- STDERR ---\n%s\n' % (rc, time.time() - t0, out, err))
print('rc=%s %.1fs -> %s' % (rc, time.time() - t0, OUT))
print(out[:6000])
