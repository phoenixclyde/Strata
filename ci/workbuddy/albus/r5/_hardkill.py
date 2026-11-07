import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
kill -9 852422 2>/dev/null; sleep 1
pkill -9 -f "ab_p3" 2>/dev/null; pkill -9 -f "w776_bench" 2>/dev/null; sleep 2
ps -ef | grep -E "[a]b_p3|[w]776_bench" | head -3
echo "--- names ---"
docker ps -a --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep -E "strata166-407" | head -4
'''))
