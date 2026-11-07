# -*- coding: utf-8 -*-
"""W709 步18：前缀复用判别 —— 精确重发 vs 末尾追加（在现役容器上，不需重启）"""
import sys
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

PROBE = r'''
import json, time, urllib.request
BASE='http://127.0.0.1:8090/v1'
mdl=json.loads(urllib.request.urlopen(BASE+'/models',timeout=60).read().decode())['data'][0]['id']
PARA=("The principal advantage of the configuration under test is that its working set fits "
      "entirely inside the memory hierarchy of the machine, so the steady state needs no disk "
      "access at all and the throughput is limited by compute rather than by storage. ")
def post(text, mt=24):
    pl={'model':mdl,'messages':[{'role':'user','content':text}],'max_tokens':mt,
        'temperature':0.0,'stream':True,'stream_options':{'include_usage':True}}
    r=urllib.request.Request(BASE+'/chat/completions',data=json.dumps(pl).encode(),
                             headers={'Content-Type':'application/json'})
    t0=time.time(); tf=None; u=None
    with urllib.request.urlopen(r,timeout=1800) as h:
        for raw in h:
            ln=raw.decode('utf-8','replace').strip()
            if not ln.startswith('data:'): continue
            d=ln[5:].strip()
            if d=='[DONE]': break
            try: j=json.loads(d)
            except Exception: continue
            if j.get('usage'): u=j['usage']
            for c in (j.get('choices') or []):
                dc=c.get('delta') or {}
                if dc.get('content') or dc.get('reasoning_content'):
                    if tf is None: tf=time.time()
    u=u or {}
    return dict(pt=u.get('prompt_tokens'), ttft=(tf-t0) if tf else -1,
                cached=((u.get('prompt_tokens_details') or {}).get('cached_tokens')))
H="Read the following text and answer with exactly one sentence.\n\n[salt-%s]\n" 
B=(PARA*150)+"\n\nQuestion: what is the principal advantage described?"
def go(tag, salt, extra=''):
    r=post(H%salt + B + extra)
    print('  %-22s pt=%-6s ttft=%7.3fs cached=%s' % (tag, r['pt'], r['ttft'], r['cached']), flush=True)
print('=== 前缀复用判别（现役 config）===', flush=True)
go('1 COLD  (salt-A)', 'A')
go('2 IDENT (salt-A 原样重发)', 'A')
go('3 APPEND(salt-A + 追加一句)', 'A', '\n\nNow add one more sentence about the same advantage.')
go('4 COLD  (salt-B 换盐)', 'B')
go('5 APPEND(salt-B + 追加一句)', 'B', '\n\nNow add one more sentence about the same advantage.')
'''
rc, out, err = _sshutil.run_remote('docker exec strata166-402 python3 -u -c %s' % _shell_quote(PROBE)
                                   if False else PROBE, timeout=900, host='192.168.50.166')
print(out)
if err.strip():
    print('--- STDERR ---'); print(err[:600])
