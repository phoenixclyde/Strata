import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
echo "=== 温度/频率/功耗 ==="
/opt/rocm/bin/rocm-smi --showtemp --showclocks --showpower 2>/dev/null | grep -E "Temperature|sclk|mclk|Power|GPU\[" | head -14
echo "=== 传感器原文 ==="
/opt/rocm/bin/rocm-smi -a 2>/dev/null | grep -iE "edge|junction|mem|hotspot|sclk|mclk|average" | head -12
''', t=90))
