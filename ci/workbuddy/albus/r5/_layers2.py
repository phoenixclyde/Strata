import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
P=/home/albus/strata166/data/packs/huihui-ud-iq4_xs/index.txt
echo "=== blk.3 的 tensor 名单 ==="
grep -E '^blk\.3\.' $P | awk '{print $1}' | head -20
echo "=== blk.0 的 tensor 名单 ==="
grep -E '^blk\.0\.' $P | awk '{print $1}' | head -20
echo "=== 每层 tensor 计数（前 8 层）==="
for i in 0 1 2 3 4 5 6 7; do printf "blk.%s: %s\n" "$i" "$(grep -cE \"^blk\.$i\.\" $P)"; done
'''))
