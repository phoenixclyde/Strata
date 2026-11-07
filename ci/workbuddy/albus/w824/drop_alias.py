import json, os, shutil

P = '/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
shutil.copyfile(P, '/home/albus/strata166/data/w824_pre_noalias.json')
d = json.load(open(P))
print('before: model_name=%r aliases=%r' % (d.get('model_name'), d.get('aliases')))
d['model_name'] = 'qwen3.8-flash-next-ud-q4_k_xl-abliterated'
d.pop('aliases', None)          # 不保留旧名
json.dump(d, open(P + '.tmp', 'w'), indent=2, ensure_ascii=False)
os.replace(P + '.tmp', P)
d2 = json.load(open(P))
print('after : model_name=%r aliases=%r' % (d2.get('model_name'), d2.get('aliases')))
print('args  :', ' '.join(map(str, d2['args']))[:120], '...')
print('env_n :', len(d2['env']), 'MMQ_KQ=', d2['env'].get('STRATA_MMQ_KQ'))
