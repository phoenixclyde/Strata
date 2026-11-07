import subprocess, base64
def sh(s, t=150):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''curl -s --max-time 8 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json
d=json.load(sys.stdin); e=d.get('engine') or {}
for k in ('kv','kv_resident','context','conversation_cache_mib','conversation_cache_slots','conversation_cache_min_tokens','expert_cache_mib','expert_slots','arena_mib'):
    print(k,'=',json.dumps(e.get(k),ensure_ascii=False)[:200])
"
echo "=== 配置里的 conversation-cache 参数 ==="
python3 -c "
import json
d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
a=d.get('args') or d.get('argv') or {}
print(json.dumps(a,ensure_ascii=False)[:600])
"
echo "=== 引擎日志里的 conversation cache 行 ==="
grep -a -iE "conversation (cache|park)|parked|kv reuse|snapshot" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -6 | cut -c1-200''', t=120))
