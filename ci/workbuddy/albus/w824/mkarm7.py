import json, copy, os

base = json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
OUT = '/home/albus/strata166/data/w824arm'
KL = '/home/albus/strata166/data/w824kl2'
os.makedirs(OUT, exist_ok=True)
os.makedirs(KL, exist_ok=True)


def mk(name, reduce12):
    d = copy.deepcopy(base)
    d['log'] = '/data/w824_%s.log' % name
    # W803 的结论：share=auto 让 prefill 逐次不同；share=0 时 LOGPOS 两遍完全相同。
    # 质量门必须先把底噪压到 0，否则效应（0.03 量级）淹没在噪声（0.03 量级）里。
    d['env']['STRATA_PREFILL_CPU_SHARE'] = '0'
    d['env']['STRATA_LOGPOS'] = '/data/w824kl2/w803_logpos_%s.tsv' % name
    d['env']['STRATA_LOGPOS_TOPK'] = '64'
    d['env'].pop('STRATA_PREFILL_TIMING', None)
    d['env'].pop('STRATA_DECODE_TIMING', None)
    if reduce12:
        d['env']['STRATA_GFX906_ATTN_REDUCE12'] = '1'
    else:
        d['env'].pop('STRATA_GFX906_ATTN_REDUCE12', None)
    json.dump(d, open(os.path.join(OUT, name + '.json'), 'w'), indent=2, ensure_ascii=False)
    print('%-4s reduce12=%-4s share=%s env=%d' % (name, d['env'].get('STRATA_GFX906_ATTN_REDUCE12', 'off'),
                                                  d['env']['STRATA_PREFILL_CPU_SHARE'], len(d['env'])))


mk('K1', True)
mk('K0', False)
mk('K1b', True)
