import subprocess, base64
def sh(s, t=60):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
date +%H:%M:%S
ps -ef | grep -E "[p]rodchk|[w]776_bench" | head -4
echo "=== health ==="
curl -s --max-time 5 http://127.0.0.1:8090/health; echo
echo "=== metrics reqs ==="
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;d=json.load(sys.stdin);r=d.get('requests') or [];print('n',len(r));[print(x.get('prompt_tokens'),x.get('prompt_ms'),x.get('decode_tok_s'),x.get('reused')) for x in r[:4]]" 2>&1 | head -8
echo "=== log tail ==="
tail -c 1200 /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
'''))
