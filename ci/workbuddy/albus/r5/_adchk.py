import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
f=$(ls -t /home/albus/strata166/data/w792_adopt_*.txt 2>/dev/null | head -1); echo FILE=$f
grep -a -E "===|health|env_|range env|f16 range|FP16 in and out|\[M\] run1|slots|governor|final installed|DONE" "$f" 2>/dev/null | cut -c1-260
'''))
