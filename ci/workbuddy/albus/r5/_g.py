import sys
sys.path.insert(0, "albus/r5")
from _rsh import sh
print(sh(r'''
curl -s --max-time 300 http://127.0.0.1:8090/v1/chat/completions \
 -H 'Content-Type: application/json' \
 -d '{"model":"qwen3.8-flash-next-ud-iq4_xs-abliterated","messages":[{"role":"user","content":"用一句话说明你会做什么。"}],"max_tokens":24,"temperature":0}' \
 | python3 -c "import sys,json;d=json.load(sys.stdin);print('OK finish=',d['choices'][0].get('finish_reason'));print((d['choices'][0]['message'].get('content') or '')[:80])"
curl -s http://127.0.0.1:8090/metrics | python3 -c "
import sys,json;m=json.load(sys.stdin);r=(m.get('requests') or [{}])[0]
print({k:r.get(k) for k in ('prompt_ms','decode_ms','decode_tok_s','reused','hit_rate')})
print('conv_cache', m.get('conversation_cache'))"
''', t=330))
