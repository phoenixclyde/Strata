import subprocess, base64, hashlib

src = open(r'D:/workbuddy_space/strata_ws/albus/r4/rw.cpp', 'rb').read()
b64 = base64.b64encode(src).decode('ascii')

SCRIPT = r'''
mkdir -p /home/albus/strata166/routerbuild
echo '%s' | base64 -d > /home/albus/strata166/routerbuild/rw.cpp
md5sum /home/albus/strata166/routerbuild/rw.cpp
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  -v /home/albus/strata166/routerbuild:/out --entrypoint bash strata-gfx906:0.2.4 -lc '
cd /out
/opt/rocm/bin/hipcc -std=c++20 -O3 -D__HIP_PLATFORM_AMD__=1 --offload-arch=gfx906 \
  -I/src/include -I/src/include/strata -I/src/include/strata/hip_compat -I/src/src \
  -o rw rw.cpp /src/src/kernels/cuda/router_top10.cu 2>&1 | tail -15
if [ -x ./rw ]; then echo BUILD_OK; ./rw 2>&1 | tail -20; echo "rc=$?"; else echo BUILD_FAIL; fi
'
''' % b64


def run(script, timeout=600):
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode('utf-8', 'replace')


print(run(SCRIPT))
print('local md5', hashlib.md5(src).hexdigest())
