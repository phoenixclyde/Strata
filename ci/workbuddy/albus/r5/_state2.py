import subprocess, base64
def sh(s, t=60):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=8","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
date +%H:%M:%S
echo "=== procs ==="
ps -ef | grep -E "[a]b_p3b|[w]776_bench" | head -3
echo "=== container ==="
docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep strata166 | head -2
echo "=== health ==="
curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 110; echo
echo "=== load/gpu ==="
cat /proc/loadavg
/opt/rocm/bin/rocm-smi --showuse 2>/dev/null | grep -i "gpu use" | head -1
'''))
