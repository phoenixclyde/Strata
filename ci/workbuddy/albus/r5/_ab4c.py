import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
f=$(ls -t /home/albus/strata166/data/w794_ab_*b*.txt 2>/dev/null | head -1); [ -z "$f" ] && f=$(ls -t /home/albus/strata166/data/w794_ab_*.txt | head -1)
echo FILE=$f
grep -a -E "=== ARM|health|\[M\] run1|attn-query|attn-reduce|det_out" "$f" 2>/dev/null | cut -c1-150
'''))
