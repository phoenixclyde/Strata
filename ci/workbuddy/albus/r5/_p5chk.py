import subprocess, base64, sys
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
out = sh(r'''
f=$(ls -t /home/albus/strata166/data/w795_ab_*.txt 2>/dev/null | head -1)
echo "FILE=$f"
[ -n "$f" ] && grep -a -E "=== ARM|arm [ABC] env|prompt chunk auto|health|warm|run1|tokens =|RESTORE" "$f" | cut -c1-190
echo "--- proc ---"; ps -ef | grep -c "[a]b_p5.sh"
''')
print(out if out.strip() else "<empty>")
