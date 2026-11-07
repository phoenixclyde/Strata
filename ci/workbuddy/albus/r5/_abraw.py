import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
f=$(ls -t /home/albus/strata166/data/w793_ab_*.txt | head -1)
sed -n '1,40p' "$f" | cut -c1-200
echo "=== live env ==="
python3 -c "import json;print(sorted(json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json')).get('env',{}).items()))"
echo "=== engine start times ==="
grep -a "engine started" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -4 | cut -c1-90
'''))
