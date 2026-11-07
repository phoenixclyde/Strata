import json, re

p = '/data/strata-huihui-ud-iq4_xs.json'
d = json.load(open(p))
print('=== 配置里所有非 args/env 的字段 ===')
for k, v in d.items():
    if k in ('env', 'args'):
        continue
    print('  %-14s = %s' % (k, str(v)[:110]))

src = open('/src/serve/server.py', encoding='utf-8', errors='replace').read().splitlines()
print()
print('=== server.py 里模型名的构造点 ===')
pat = re.compile(r'abliterated|model_id|model_name|modelName|"id"|/v1/models|families|name_of|display')
for i, l in enumerate(src, 1):
    if pat.search(l):
        print('%5d %s' % (i, l.rstrip()[:150]))
