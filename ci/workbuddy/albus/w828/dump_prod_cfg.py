import json
c = json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
a = c['args']
pairs = {}
i = 0
while i < len(a):
    k = a[i]
    if k.startswith('--'):
        v = a[i + 1] if i + 1 < len(a) and not a[i + 1].startswith('--') else ''
        pairs[k] = v
        i += 2 if v else 1
    else:
        i += 1
print(json.dumps({'exe': c.get('exe'), 'args': pairs, 'env': c.get('env') or {},
                  'nargs': len(a)}, ensure_ascii=False, indent=1))
