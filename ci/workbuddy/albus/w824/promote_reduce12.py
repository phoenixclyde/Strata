import json, os, shutil

P = '/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
shutil.copyfile(P, '/home/albus/strata166/data/w824_pre_reduce12.json')
d = json.load(open(P))
before = d['env'].get('STRATA_GFX906_ATTN_REDUCE12')
d['env']['STRATA_GFX906_ATTN_REDUCE12'] = '1'
# 相位表不进生产：默认关闭（测完就撤）
d['env'].pop('STRATA_PREFILL_TIMING', None)
d['env'].pop('STRATA_DECODE_TIMING', None)
json.dump(d, open(P + '.tmp', 'w'), indent=2, ensure_ascii=False)
os.replace(P + '.tmp', P)
d2 = json.load(open(P))
print('REDUCE12: %r -> %r' % (before, d2['env'].get('STRATA_GFX906_ATTN_REDUCE12')))
print('env_n =', len(d2['env']), '| TIMING 残留:', [k for k in d2['env'] if 'TIMING' in k] or '无')
print('exe =', d2['exe'], '| model_name =', d2['model_name'], '| aliases =', d2.get('aliases'))
