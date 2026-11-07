import subprocess, base64

SCRIPT = r'''
mkdir -p /home/albus/strata166/routerbuild
chmod 777 /home/albus/strata166/routerbuild
docker run --rm \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -v /home/albus/strata166/routerbuild:/out \
  --entrypoint bash strata-gfx906:0.2.4 -lc '
set -u
cd /out
HCC=$(command -v hipcc || echo /opt/rocm/bin/hipcc)
echo "hipcc=$HCC"
$HCC -std=c++20 -O3 -D__HIP_PLATFORM_AMD__=1 --offload-arch=gfx906 \
  -I/src/include -I/src/include/strata -I/src/include/strata/hip_compat -I/src/src \
  -o rfast /src/tests/hip/router_fast.cpp /src/src/kernels/cuda/router_top10.cu 2>&1 | tail -25
if [ -x ./rfast ]; then echo BUILD_OK; ./rfast 2>&1 | tail -40; else echo BUILD_FAIL; fi
'
'''


def run(script, timeout=600):
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode('utf-8', 'replace')


print(run(SCRIPT))
