python3 - <<'PY'
import json
s=open('/home/albus/strata166/data/w828_calib_run1.out',encoding='utf-8',errors='replace').read()
i=s.find('{')
dec=json.JSONDecoder()
j,_=dec.raw_decode(s[i:])
print('settings', json.dumps(j.get('settings'), indent=1))
print('env', json.dumps(j.get('env')))
r=j.get('report') or {}
print('report keys', list(r))
for k,v in r.items():
    txt=json.dumps(v)
    print('  %-14s %s' % (k, txt[:260]))
PY
