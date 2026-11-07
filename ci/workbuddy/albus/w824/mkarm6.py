import json, copy, os

base = json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
OUT = '/home/albus/strata166/data/w824arm'
KL = '/home/albus/strata166/data/w824kl'
os.makedirs(OUT, exist_ok=True)
os.makedirs(KL, exist_ok=True)


def mk(name, reduce12):
    d = copy.deepcopy(base)
    d['log'] = '/data/w824_%s.log' % name
    d['env']['STRATA_LOGPOS'] = '/data/w824kl/w803_logpos_%s.tsv' % name
    d['env']['STRATA_LOGPOS_TOPK'] = '64'
    # 相位表不进这一轮（会往 stderr 写大量行，且与 KL 无关）
    d['env'].pop('STRATA_PREFILL_TIMING', None)
    d['env'].pop('STRATA_DECODE_TIMING', None)
    if reduce12:
        d['env']['STRATA_GFX906_ATTN_REDUCE12'] = '1'
    else:
        d['env'].pop('STRATA_GFX906_ATTN_REDUCE12', None)
    json.dump(d, open(os.path.join(OUT, name + '.json'), 'w'), indent=2, ensure_ascii=False)
    print('%-4s reduce12=%-3s env=%d logpos=%s' % (name, d['env'].get('STRATA_GFX906_ATTN_REDUCE12', 'off'),
                                                   len(d['env']), d['env']['STRATA_LOGPOS']))


mk('Q1', True)
mk('Q0', False)
mk('Q1b', True)
