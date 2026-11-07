import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''curl -s --max-time 8 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json,statistics
d=json.load(sys.stdin); r=d.get('requests') or []
r=list(reversed(r))
print('%-3s %8s %8s %9s %9s %9s %8s'%('i','prompt_t','reused','prompt_ms','decode_ms','dec_tok_s','dur_s'))
rows=[]
for i,x in enumerate(r,1):
    print('%-3d %8s %8s %9s %9s %9s %8s'%(i,x.get('prompt_tokens'),x.get('reused'),x.get('prompt_ms'),x.get('decode_ms'),x.get('decode_tok_s'),x.get('duration_s')))
    if x.get('reused') and x.get('decode_tok_s'): rows.append(x['decode_tok_s'])
if len(rows)>2:
    print()
    print('复用轮 decode_tok_s: n=%d med=%.2f min=%.2f max=%.2f 极差=%.2f%%'%(len(rows),statistics.median(rows),min(rows),max(rows),(max(rows)/min(rows)-1)*100))
"'''))
