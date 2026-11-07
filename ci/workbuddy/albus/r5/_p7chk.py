import subprocess, base64, re
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
raw = sh(r'''
f=$(ls -t /home/albus/strata166/data/w797_ab_*.txt 2>/dev/null | head -1); echo FILE=$f
[ -n "$f" ] && grep -a -E "^=== |^arm |^health|prompt_ms=|strata prefill timing|depth|FOUND|not found" "$f" | cut -c1-110
echo "--- proc ---"; ps -ef | grep -c "[a]b_p7.sh"
''')
print(raw[-3000:])
