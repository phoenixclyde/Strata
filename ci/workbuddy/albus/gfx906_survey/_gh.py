import json,urllib.request,urllib.parse,sys,time
TOK=open(r'D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt').read().strip()
def gh(path, **q):
    u='https://api.github.com'+path
    if q: u+='?'+urllib.parse.urlencode(q)
    r=urllib.request.Request(u,headers={'Authorization':'Bearer '+TOK,'Accept':'application/vnd.github+json','User-Agent':'albus'})
    for i in range(4):
        try:
            return json.load(urllib.request.urlopen(r,timeout=40))
        except urllib.error.HTTPError as e:
            body=e.read()[:300].decode('utf8','ignore')
            if e.code in (403,429):
                print('RATE/ERR',e.code,body,file=sys.stderr); time.sleep(20); continue
            raise
