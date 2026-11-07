import json, os, shutil

P = '/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
OLD = 'qwen3.8-flash-next-ud-iq4_xs-abliterated'
NEW = 'qwen3.8-flash-next-ud-q4_k_xl-abliterated'

shutil.copyfile(P, '/home/albus/strata166/data/w824_modelname_backup.json')
d = json.load(open(P))
before = d.get('model_name')
d['model_name'] = NEW
# 保留旧名做别名：客户端里已经填了旧名的不会被 /v1/chat/completions 的 model 校验拒绝
al = d.get('aliases')
if isinstance(al, str):
    al = [x.strip() for x in al.split(',') if x.strip()]
elif isinstance(al, list):
    al = list(al)
else:
    al = []
if OLD not in al:
    al.append(OLD)
d['aliases'] = al
json.dump(d, open(P + '.tmp', 'w'), indent=2, ensure_ascii=False)
os.replace(P + '.tmp', P)
print('model_name: %r -> %r' % (before, d['model_name']))
print('aliases   :', d['aliases'])
print('args unchanged:', '--pack /data/packs/ud-q4_k_xl' in ' '.join(map(str, d['args'])))
