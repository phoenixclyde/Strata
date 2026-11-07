import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
cd /home/albus/strata166/data
ls -la --time-style=+%m-%d_%H:%M | awk '$6 ~ /10-25/ {print $5, $6, $7}' | sort -k2 | tail -40
'''))
