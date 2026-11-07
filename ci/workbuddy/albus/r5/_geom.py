import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== geometry 行 ==="
grep -a -iE "n_embd|n_head|head_dim|n_layer|n_ff|qsa|qwen3.8|geom" "$L" | head -12 | cut -c1-220
echo "=== 配置里的 args ==="
python3 -c "import json;print(json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json')).get('args'))"
'''))
