import json, os, shutil

P = '/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
NEW = '/data/bin/strata-0.1.53'
shutil.copyfile(P, '/home/albus/strata166/data/w824_pre_promote.json')
d = json.load(open(P))
old = d.get('exe')
d['exe'] = NEW
json.dump(d, open(P + '.tmp', 'w'), indent=2, ensure_ascii=False)
os.replace(P + '.tmp', P)
d2 = json.load(open(P))
print('exe: %s -> %s' % (old, d2['exe']))
print('model_name =', d2['model_name'], '| aliases =', d2.get('aliases'))
print('args =', len(d2['args']), 'env =', len(d2['env']), '| TIMING in env:', 'STRATA_PREFILL_TIMING' in d2['env'])
