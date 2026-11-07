import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== mmq / expert fmt lines ==="
grep -a -i -E "MMQ|expert.*format|prompt kernels|IQ4_XS|IQ3_S" "$L" | tail -12 | cut -c1-230
echo "=== engine version / start ==="
grep -a -E "engine started|strata 0" "$L" | tail -3 | cut -c1-120
'''))
