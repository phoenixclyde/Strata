import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
f=$(ls -t /home/albus/strata166/data/r5_ab_*.txt | head -1)
tail -12 "$f"
echo "=== live env ==="
python3 -c "import json;print(sorted(json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json')).get('env',{}).items()))"
md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
ps -ef | grep -c "[p]f_ab.sh"
'''))
