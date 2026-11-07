import subprocess, base64

SCRIPT = r'''
echo "=== CU COUNT ==="
/opt/rocm/bin/rocminfo 2>/dev/null | grep -c "Compute Unit" 
/opt/rocm/bin/rocminfo 2>/dev/null | grep -A2 "gfx906" | head -6
echo "=== LDS per CU ==="
/opt/rocm/bin/rocminfo 2>/dev/null | grep -m2 -i "worksize\|lds\|Local"
echo "=== r5 binary md5 ==="
docker run --rm --entrypoint sh strata-gfx906:0.2.4r5 -c 'md5sum /src/build-906/strata; ls -l /src/build-906/strata | awk "{print \$5}"' 2>&1 | head -4
echo "=== 0.2.4 binary md5 ==="
docker run --rm --entrypoint sh strata-gfx906:0.2.4 -c 'md5sum /src/build-906/strata; ls -l /src/build-906/strata | awk "{print \$5}"' 2>&1 | head -4
'''


def run(script):
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'albus@192.168.50.166', 'base64 -d | bash'],
                       input=base64.b64encode(script.encode()), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=300)
    return p.stdout.decode('utf-8', 'replace')


print(run(SCRIPT))
