python3 - <<'PY'
import json, os
src='/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
base=json.load(open(src))
print('prod exe:', base['exe'])

def mk(name, exe, overrides=None, extra_args=None, extra_env=None):
    c=json.loads(json.dumps(base))
    c['exe']=exe
    c['log']='/data/%s.log' % name
    if overrides:
        c.update(overrides)
    if extra_args:
        c['args']=c['args']+extra_args
    if extra_env:
        c.setdefault('env',{}).update(extra_env)
    p='/home/albus/strata166/data/%s.json' % name
    json.dump(c, open(p,'w'), ensure_ascii=False, indent=1)
    print('wrote', p, 'exe=', c['exe'], 'args=', len(c['args']), 'env=', len(c['env']))
    return p

mk('w828_a153', '/data/bin/strata-0.1.53')
mk('w828_b154n', '/data/bin/strata-0.1.54n')
# wide build arms are generated only once that binary exists
print('fingerprint src:', __import__('hashlib').md5(open(src,'rb').read()).hexdigest()[:16])
PY
echo "--- measurement corpus ---"
ls -la /home/albus/strata166/tmp/mt_gen.py /home/albus/strata166/tmp/mt_read.py /home/albus/strata166/tmp/kl_pool.json /home/albus/strata166/tmp/dec_corpus.json 2>&1
ls /home/albus/strata166/tmp/ | head -20
