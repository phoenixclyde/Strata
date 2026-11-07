import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== 日志里涉及 layer 计数的行 ==="
grep -a -iE "[0-9]+ (gdn|qsa|linear|full)[a-z-]* layers|layers: [0-9]|attention layers" "$L" | tail -6 | cut -c1-200
echo "=== 最近的启动段（17:32 那次）前 40 行 ==="
awk '/17:32:.*engine started/{f=1} f&&c<40{print; c++}' "$L" | cut -c1-180
'''))
