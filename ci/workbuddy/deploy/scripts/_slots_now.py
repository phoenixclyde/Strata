import sys, json, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
OFF = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def get(path, timeout=15):
    with OFF.open(urllib.request.Request('http://192.168.50.166:8090' + path), timeout=timeout) as r:
        return r.status, r.read().decode('utf-8', 'replace')

try:
    st, body = get('/v1/status')
    print('HTTP', st)
    try:
        d = json.loads(body)
        print(json.dumps(d, ensure_ascii=False, indent=1)[:3000])
    except Exception:
        print(body[:3000])
except Exception as e:
    print('STATUS_FAIL', str(e)[:200])

print()
try:
    st, body = get('/v1/models')
    print('MODELS HTTP', st)
    print(body[:800])
except Exception as e:
    print('MODELS_FAIL', str(e)[:200])
