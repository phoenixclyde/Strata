set -e
mkdir -p /home/albus/strata166/data/w828kl
cd /home/albus/strata166
python3 - <<'PY'
import json, os
pool=json.load(open('/home/albus/strata166/tmp/kl_pool.json'))
texts=[t for t in pool if isinstance(t,str)] if isinstance(pool,list) else [k for k in pool]
texts=sorted(texts, key=len, reverse=True)
# one long prompt: ~4.5k tokens at ~3.5 chars/token
target=15800
parts=[]; n=0
for t in texts:
    parts.append(t); n+=len(t)+1
    if n>=target: break
prompt=' '.join(parts)
json.dump({'prompt': prompt, 'chars': len(prompt)}, open('/home/albus/strata166/tmp/kl_long.json','w'))
print('prompt chars', len(prompt), 'est tokens', len(prompt)//3.5)

base=json.load(open('/home/albus/strata166/data/w828_ta.json'))

def mk(name, out_tsv, minimal=False):
    c=json.loads(json.dumps(base))
    c['log']='/data/%s.log' % name
    c['env']=dict(c['env'])
    c['env']['STRATA_PREFILL_CPU_SHARE']='0'      # the hard prerequisite: otherwise the noise (0.025) is the size of the effect
    c['env']['STRATA_LOGPOS']=out_tsv
    c['env']['STRATA_LOGPOS_TOPK']='64'
    if minimal:
        c['env']['STRATA_ROUTE_TAIL_SKIP']='0'
        c['env']['STRATA_HIP_PROMPT_F16']='0'
        c['env']['STRATA_SELECT_SIMT']='0'
        c['env']['STRATA_HC_Q8']='0'
        a=c['args']
        if '--kv' in a:
            i=a.index('--kv'); a[i+1]='fp16'
    json.dump(c, open('/home/albus/strata166/data/%s.json'%name,'w'), ensure_ascii=False, indent=1)
    print(name, 'kv=', c['args'][c['args'].index('--kv')+1] if '--kv' in c['args'] else '?',
          'rt_skip=', c['env'].get('STRATA_ROUTE_TAIL_SKIP'), 'f16=', c['env'].get('STRATA_HIP_PROMPT_F16'),
          'simt=', c['env'].get('STRATA_SELECT_SIMT'), 'hcq8=', c['env'].get('STRATA_HC_Q8'))

mk('w828_kle0',  '/data/w828kl/E0.tsv')
mk('w828_kle0b', '/data/w828kl/E0b.tsv')
mk('w828_kleall','/data/w828kl/Eall.tsv', minimal=True)
PY
ls -la /home/albus/strata166/data/w828_kle*.json
