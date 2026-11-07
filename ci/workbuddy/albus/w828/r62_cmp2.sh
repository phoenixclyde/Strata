python3 - <<'PY'
import json, statistics
def load(p):
    s=open(p,encoding='utf-8',errors='replace').read()
    j,_=json.JSONDecoder().raw_decode(s[s.find('{'):])
    return j
a=load('/home/albus/strata166/data/w828_calib_run1.out')
b=load('/home/albus/strata166/data/w828_calib2.out')
print('=== settings ===')
print('run1', json.dumps(a.get('settings')))
print('     env', json.dumps(a.get('env')))
print('run2', json.dumps(b.get('settings')))
print('     env', json.dumps(b.get('env')))
print()
print('=== default (engine\'s own choice) ===')
print('run1', json.dumps(a['report']['default']))
print('run2', json.dumps(b['report']['default']))
print()
for key in ('pcie_sweep','min_p_sweep','workers','adapt','sh_stream'):
    print('===',key,'===')
    ra=a['report'].get(key) or {}
    rb=b['report'].get(key) or {}
    for k in sorted(set(ra)|set(rb), key=str):
        va=ra.get(k); vb=rb.get(k)
        ma = statistics.median(va) if isinstance(va,list) and va else va
        mb = statistics.median(vb) if isinstance(vb,list) and vb else vb
        print('  %-10s run1 %s   run2 %s' % (k, ('%.2f'%ma) if isinstance(ma,float) else ma,
                                              ('%.2f'%mb) if isinstance(mb,float) else mb))
print()
print('=== confirm ===')
for name,j in (('run1',a),('run2',b)):
    c=j['report'].get('confirm') or {}
    print(name, {k:[round(x,2) for x in v] for k,v in c.items()},
          '-> medians', {k:round(statistics.median(v),2) for k,v in c.items()})
print()
print('seconds run1 %s run2 %s' % (a['report'].get('seconds'), b['report'].get('seconds')))
PY
