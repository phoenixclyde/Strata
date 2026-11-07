import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
f=$(ls -t /home/albus/strata166/data/w798c_phase_*.txt 2>/dev/null | head -1); echo FILE=$f
[ -n "$f" ] && grep -a -E "^=== ARM|slots |^build|^  r[1-4]|^=== RESTORE|^=== DONE" "$f" | cut -c1-120
echo "--- stages 行数 ---"; [ -n "$f" ] && grep -ac "decode GPU stages" "$f"
echo "--- proc ---"; ps -ef | grep -c "[a]b_p8c"
'''))
