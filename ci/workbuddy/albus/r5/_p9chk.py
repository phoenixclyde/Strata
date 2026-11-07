import subprocess, base64
def sh(s, t=150):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
f=$(ls -t /home/albus/strata166/data/w799_gain_*.txt 2>/dev/null | head -1); echo FILE=$f
[ -n "$f" ] && grep -a -E "^=== |^gain |park_lines|build:|^ +[0-9]+ +[0-9]+ |parked |superseded" "$f" | cut -c1-125
echo "--- proc ---"; ps -ef | grep -c "[a]b_p9"
'''))
