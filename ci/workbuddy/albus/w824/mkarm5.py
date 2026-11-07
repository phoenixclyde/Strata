import json, copy, os

base = json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
OUT = '/home/albus/strata166/data/w824arm'
NEW = '/data/bin/strata-0.1.53'


def mk(name, env=None, pairs=None):
    d = copy.deepcopy(base)
    d['exe'] = NEW
    d['log'] = '/data/w824_%s.log' % name
    d['env']['STRATA_PREFILL_TIMING'] = '1'
    d['env']['STRATA_DECODE_TIMING'] = '1'      # 解码分解（ms/window + verify/host/draft），抗 wall 漂移
    if env:
        d['env'].update(env)
    a = d['args']
    if pairs:
        for k, v in pairs.items():
            a[a.index(k) + 1] = str(v)
    json.dump(d, open(os.path.join(OUT, name + '.json'), 'w'), indent=2, ensure_ascii=False)
    print('%-4s env=%d args[13]=%r  改动=%s' % (name, len(d['env']), a[13], env or pairs or '无(基线)'))


mk('N1')
mk('A1', env={'STRATA_GFX906_ATTN_REDUCE12': '1'})     # attn 分块：prefill+verify+MTP
mk('V1', env={'STRATA_EXPERT_V2K': '1'})               # Q4_K 的 V2K 解码内核（再测，这次带解码分解）
