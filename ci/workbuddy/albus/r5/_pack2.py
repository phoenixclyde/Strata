import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
P=/home/albus/strata166/data/packs/huihui-ud-iq4_xs
head -20 "$P/native_experts.txt"
echo "=== unique types ==="
awk '{print $2, $3, $4}' "$P/native_experts.txt" 2>/dev/null | sort | uniq -c | head
echo "=== index.txt sample (expert lines) ==="
grep -a -m 6 -i "expert" "$P/index.txt" | cut -c1-160
'''))
