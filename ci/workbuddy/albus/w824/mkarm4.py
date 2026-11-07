import json, copy, os

base = json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
OUT = '/home/albus/strata166/data/w824arm'
NEW = '/data/bin/strata-0.1.53'


def mk(name, env=None, pairs=None):
    d = copy.deepcopy(base)
    d['exe'] = NEW
    d['log'] = '/data/w824_%s.log' % name
    d['env']['STRATA_PREFILL_TIMING'] = '1'
    if env:
        d['env'].update(env)
    a = d['args']
    if pairs:
        for k, v in pairs.items():
            a[a.index(k) + 1] = str(v)          # args 必须是字符串（T2 上次就是这里崩的）
    json.dump(d, open(os.path.join(OUT, name + '.json'), 'w'), indent=2, ensure_ascii=False)
    print('%-4s env=%d  args[12:15]=%r  V2K=%s' % (name, len(d['env']), a[12:15], d['env'].get('STRATA_EXPERT_V2K')))


mk('N0b')
mk('T1b', env={'STRATA_EXPERT_V2K': '1'})
mk('T2b', pairs={'--spec-min-p': '0.50'})
