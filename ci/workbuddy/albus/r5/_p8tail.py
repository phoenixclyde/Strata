import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
date +%H:%M:%S
f=$(ls -t /home/albus/strata166/data/w798_ab_*.txt | head -1)
tail -22 "$f" | cut -c1-130
echo "--- proc ---"; ps -ef | grep "[a]b_p8" | head -3
'''))
