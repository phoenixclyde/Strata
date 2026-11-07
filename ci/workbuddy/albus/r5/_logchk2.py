import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -a -E "prompt|prefill" "$L" | grep -a -v "prefill timing" | tail -14 | cut -c1-240
'''))
