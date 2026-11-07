set -e
cd /home/albus/strata166
# keep run 1 for the comparison
[ -f data/w828_calib.out ] && cp -a data/w828_calib.out data/w828_calib_run1.out || true
[ -f data/w828_calib.json ] && cp -a data/w828_calib.json data/w828_calib_run1.json || true
ls -la data/w828_calib_run1.out data/w828_calib_run1.json 2>/dev/null
echo "--- run1 settings ---"
python3 - <<'PY'
import json, re
s=open('/home/albus/strata166/data/w828_calib_run1.out',encoding='utf-8',errors='replace').read()
i=s.find('{\n "settings"')
if i<0: i=s.find('"settings"')
j=json.loads(s[s.rfind('{', 0, i+12):]) if i>=0 else {}
print(json.dumps(j.get('settings'), indent=1))
print('env', json.dumps(j.get('env')))
r=j.get('report') or {}
print('report keys', list(r))
for k in ('pcie_sweep','spec_sweep','workers','adapt','sh_stream'):
    if k in r: print(k, '->', json.dumps(r[k])[:300])
PY
