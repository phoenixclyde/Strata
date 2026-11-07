import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
cd /home/albus/strata166/data
ls -la w789* w790* w791* w792* w793* w794* w795* 2>/dev/null | awk '{print $5, $9}'
echo "=== r5_/r0_ files ==="
ls -la r5_* r0_* 2>/dev/null | awk '{print $5, $9}' | head -20
'''))
