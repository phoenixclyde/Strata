import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
pkill -9 -f ab_p4b 2>/dev/null; sleep 2; pkill -9 -f w776_bench 2>/dev/null; sleep 1
ps -ef | grep -E "[a]b_p4b|[w]776_bench" | head -3
docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep strata166-407 | head -2
curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 60; echo
'''))
