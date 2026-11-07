python3 - <<'PY'
import json, time, urllib.request

B='http://127.0.0.1:8090'

def post(body, timeout=300):
    r=urllib.request.Request(B+'/v1/chat/completions', data=json.dumps(body).encode(),
                             headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read())

model=json.loads(urllib.request.urlopen(B+'/v1/models',timeout=10).read())['data'][0]['id']
print('model', model)

t0=time.time()
j=post({'model':model,'messages':[{'role':'user','content':'用一句话说明你能做什么。'}],
        'max_tokens':48,'temperature':0.0})
u=j.get('usage',{})
print('chat %.1fs  finish=%s  tokens=%s' % (time.time()-t0, j['choices'][0].get('finish_reason'), u))
print('text:', (j['choices'][0]['message'].get('content') or '')[:160].replace('\n',' '))

tools=[{'type':'function','function':{
    'name':'get_weather','description':'Get the current weather for a city.',
    'parameters':{'type':'object','properties':{'city':{'type':'string'},
                  'days':{'type':'array','items':{'type':'integer'}}},'required':['city']}}}]
t0=time.time()
j2=post({'model':model,'messages':[{'role':'user','content':'用 get_weather 查北京未来两天的天气。'}],
         'tools':tools,'tool_choice':'auto','max_tokens':160,'temperature':0.0})
m=j2['choices'][0]['message']
tc=m.get('tool_calls')
print('tool test %.1fs finish=%s tool_calls=%s' % (time.time()-t0, j2['choices'][0].get('finish_reason'),
      json.dumps(tc,ensure_ascii=False)[:300] if tc else None))
if not tc:
    print('  (no call; content:)', (m.get('content') or '')[:200].replace('\n',' '))
PY
echo "--- serve-side tool counters in the log ---"
docker logs strata166-407 2>&1 | grep -a -E "tool call|tool_args_repaired|tool_call_recovery" | tail -5 | cut -c1-170
