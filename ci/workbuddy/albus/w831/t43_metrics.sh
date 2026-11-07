#!/bin/bash
curl -s --max-time 8 http://127.0.0.1:8090/metrics > /tmp/m.json
python3 - <<'PY'
import json
d=json.load(open('/tmp/m.json'))
def find(o,k,path=''):
    if isinstance(o,dict):
        for kk,vv in o.items():
            if kk==k: print('  found at', path+'/'+kk, '=', vv)
            find(vv,k,path+'/'+kk)
    elif isinstance(o,list):
        pass
find(d,'gpu_pcie_rx_mb')
PY
