import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
P=/home/albus/strata166/data/packs/huihui-ud-iq4_xs/index.txt
echo "attn_qkv: $(grep -c '\.attn_qkv\.weight' $P)"
echo "attn_gate: $(grep -c '\.attn_gate\.weight' $P)"
echo "gdn (conv/recurrent/linear): $(grep -cE '\.(ssm_|gdn_)' $P)"
echo "blk 层数: $(grep -oE 'blk\.[0-9]+' $P | sort -u | wc -l)"
echo "=== 各层是否有 qkv ==="
grep -oE 'blk\.[0-9]+\.attn_qkv' $P | sort -t. -k2 -n | head -20
'''))
