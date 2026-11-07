import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''pkill -9 -f ab_p8b 2>/dev/null; sleep 2; pkill -9 -f mt_decode2 2>/dev/null; sleep 1
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 200); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo ready=${i}s; break; }; sleep 1; done
ps -ef | grep -c "[a]b_p8"; curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 40''', t=300))
