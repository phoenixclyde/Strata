import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
ps -ef | grep -E "[a]b_p3|[w]776_bench" | head -5
echo "=== container ==="
docker ps -a --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep strata166 | head -3
echo "=== health ==="
curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 90; echo
echo "=== env ==="
python3 -c "import json;print(sorted(json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json')).get('env',{}).items()))"
'''))
