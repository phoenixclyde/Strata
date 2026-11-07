import subprocess, base64
def sh(s, t=150):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
f=$(ls -t /home/albus/strata166/data/w795j_ab_*.txt | head -1)
tail -6 "$f" | cut -c1-200
echo "=== all MMQ tile lines (log) ==="
grep -a "MMQ tile:" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -24 | cut -c1-140
'''))
