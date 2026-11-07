cd /home/albus/strata166/tmp
python3 - <<'PY'
import re
for f in ('mt_gen.py','mt_read.py'):
    p='/home/albus/strata166/tmp/'+f
    s=open(p,encoding='utf-8').read()
    if 'MT_MODEL_RESOLVE' in s:
        print(f,'already patched'); continue
    if f=='mt_gen.py':
        old='MODEL = "qwen3.8-flash-next-ud-iq4_xs-abliterated"'
        assert old in s, 'model line not found'
        new=('''# W828: the served name is no longer the iq4 one; read it from the server (a name the server
# does not know would 400 before anything is measured).
def _model_name(default: str) -> str:
    try:
        with urllib.request.urlopen("http://127.0.0.1:%s/v1/models" % port, timeout=10) as r:
            j = json.loads(r.read().decode())
        d = j.get("data") or []
        if d and d[0].get("id"):
            return d[0]["id"]
    except Exception:
        pass
    return default
MODEL = _model_name("qwen3.8-flash-next-ud-q4_k_xl-abliterated")   # MT_MODEL_RESOLVE''')
        s=s.replace(old,new)
    else:
        s=s.replace('body = {"model": "default-big"','body = {"model": _model_name()')
        s=s.replace('def post(text):', '''def _model_name():
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/v1/models" % PORT, timeout=10) as r:
            d = (json.loads(r.read().decode()).get("data") or [])
        if d and d[0].get("id"):
            return d[0]["id"]
    except Exception:
        pass
    return "default-big"   # MT_MODEL_RESOLVE


def post(text):''')
    open(p,'w',encoding='utf-8').write(s)
    print('patched',f)
PY
python3 -m py_compile mt_gen.py mt_read.py && echo PY_OK
grep -n 'MT_MODEL_RESOLVE' mt_gen.py mt_read.py | head
