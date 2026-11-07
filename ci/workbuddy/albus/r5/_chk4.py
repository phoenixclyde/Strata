import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
f=$(ls -t /home/albus/strata166/data/r5_pf_*.txt | head -1); echo FILE=$f
grep -a "99382 tokens" "$f" | tr ' ' '\n' | paste - - | head -40
echo "=== raw ==="
grep -a "99382 tokens" "$f"
echo "=== run line ==="
grep -a -E "^  \[L\]" "$f"
'''))
