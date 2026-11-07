import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
f=$(ls -t /home/albus/strata166/data/w794_ab_*.txt 2>/dev/null | head -1); echo FILE=$f
grep -a -E "=== ARM|new_container|p4 healthy|health|\[M\] run1|attn-query-swizzle|attn-reduce12|det_out|DONE" "$f" 2>/dev/null | cut -c1-170
'''))
