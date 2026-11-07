import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
f=$(ls -t /home/albus/strata166/data/r5_ab_*.txt 2>/dev/null | head -1); echo FILE=$f
grep -a "21822 tokens" "$f"
echo "=== arms ==="
grep -a -E "=== ARM|--- [BF] run|\[M\] run1" "$f"
'''))
