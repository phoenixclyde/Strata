import subprocess, base64

SCRIPT = r'''
echo "=== 镜像内是否有测试目标 ==="
docker run --rm --entrypoint sh strata-gfx906:0.2.4 -c '
ls -l /src/tests/hip/router_fast.cpp 2>&1 | head -2
echo "--- build tree targets ---"
ls /src/build-906/ | grep -i router | head -5
grep -c "hip_router_fast" /src/build-906/Makefile 2>/dev/null || echo "no makefile-hit"
grep -m1 "BUILD_TESTING\|STRATA_BUILD_TESTS" /src/build-906/CMakeCache.txt 2>/dev/null || echo "no-test-var"
echo "--- ninja? ---"
ls /src/build-906/build.ninja /src/build-906/Makefile 2>/dev/null
' 2>&1 | head -14
'''


def run(script, timeout=240):
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode('utf-8', 'replace')


print(run(SCRIPT))
