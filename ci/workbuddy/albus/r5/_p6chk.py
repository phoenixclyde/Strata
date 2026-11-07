import subprocess, base64, re
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
f=$(ls -t /home/albus/strata166/data/w796_ab_*.txt 2>/dev/null | head -1); echo FILE=$f
[ -n "$f" ] && grep -a -E "=== ARM|arm [ABC] env|health|prompt_ms=|prefill timing: (2182|993)|depth|found|DONE" "$f" | cut -c1-120
'''))
