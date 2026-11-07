import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
f=$(ls -t /home/albus/strata166/data/r5_ab_*.txt 2>/dev/null | head -1); echo FILE=$f
grep -a -E "=== ARM|env_now|--- [BF] run|\[M\] run1|tokens, GPU timeline|FP16 in and out|needle|✓|found" "$f" 2>/dev/null | cut -c1-230
'''))
