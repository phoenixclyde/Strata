import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
f=$(ls -t /home/albus/strata166/data/w795j_ab_*.txt | head -1)
head -14 "$f" | cut -c1-180
echo "..."
docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep strata166 | head -3
'''))
